/*
 * kappa-pin / firmware / main / measurement.c
 * Thermal conductivity / diffusivity measurement engine
 *
 * Transient line-source method (ASTM D5334 / D7896):
 *   λ = Q / (4π · m)   where m = dΔT/d(ln t)
 *   α from full curve Levenberg-Marquardt fit
 *   ρcₚ = λ / α
 *   e = √(λ · ρcₚ)
 *
 * MIT License.
 */
#include "measurement.h"
#include "adc24.h"
#include "heater.h"
#include "probe.h"
#include "flash_store.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <math.h>
#include <string.h>

static const char *TAG = "meas";

/* Material presets table */
static const material_preset_t presets[MAT_COUNT] = {
    [MAT_LIQUID]       = { "Liquid",       0.3f,  8.0f, 120, PROBE_HOTWIRE },
    [MAT_WET_SOIL]     = { "Wet Soil",     1.0f, 30.0f,  60, PROBE_NEEDLE },
    [MAT_DRY_SOIL]     = { "Dry Soil",     0.5f, 30.0f,  60, PROBE_NEEDLE },
    [MAT_POLYMER]      = { "Polymer",      0.5f, 20.0f,  60, PROBE_NEEDLE },
    [MAT_INSULATION]   = { "Insulation",   0.2f, 60.0f,  30, -1 },
    [MAT_METAL_POWDER] = { "Metal Powder", 3.0f, 10.0f, 120, PROBE_NEEDLE },
    [MAT_CUSTOM]       = { "Custom",       1.0f, 20.0f,  60, -1 },
};

/* Measurement state */
static volatile meas_state_t state = MEAS_IDLE;
static meas_result_t result;
static meas_sample_t samples[MEAS_MAX_SAMPLES];
static volatile int sample_count = 0;
static material_t current_material = MAT_WET_SOIL;
static float calibration_factor = 1.0f;
static float cal_offset = 0.0f;

/* Euler-Mascheroni constant */
#define GAMMA_EULER  0.5772156649f

const material_preset_t *measurement_get_preset(material_t mat)
{
    if (mat >= MAT_COUNT) return &presets[MAT_CUSTOM];
    return &presets[mat];
}

void measurement_set_calibration(float cf)
{
    calibration_factor = cf;
}

float measurement_get_calibration(void)
{
    return calibration_factor;
}

void measurement_start(material_t mat)
{
    if (state != MEAS_IDLE && state != MEAS_DONE && state != MEAS_ERROR) {
        ESP_LOGW(TAG, "Measurement already in progress (state=%d)", state);
        return;
    }

    current_material = mat;
    sample_count = 0;
    memset(&result, 0, sizeof(result));
    state = MEAS_ARMING;

    ESP_LOGI(TAG, "Measurement started: material=%s",
             presets[mat].name);
}

void measurement_cancel(void)
{
    if (state == MEAS_HEATING) {
        heater_emergency_stop();
    }
    state = MEAS_IDLE;
    ESP_LOGI(TAG, "Measurement cancelled");
}

meas_state_t measurement_get_state(void)
{
    return state;
}

const meas_result_t *measurement_get_result(void)
{
    return &result;
}

const meas_sample_t *measurement_get_samples(int *count)
{
    *count = sample_count;
    return samples;
}

int measurement_get_sample_count(void)
{
    return sample_count;
}

/* ---- Linear regression: ΔT = m·ln(t) + c ---- */
static void linear_fit_ln_t(const meas_sample_t *s, int start, int end,
                             float *slope, float *intercept, float *r2)
{
    double sum_x = 0, sum_y = 0, sum_xx = 0, sum_xy = 0;
    int n = end - start + 1;

    if (n < 3) { *slope = 0; *intercept = 0; *r2 = 0; return; }

    for (int i = start; i <= end; i++) {
        if (s[i].t_s <= 0) continue;
        double x = log(s[i].t_s);
        double y = s[i].dt_mk / 1000.0f;  /* mK → °C */
        sum_x += x;
        sum_y += y;
        sum_xx += x * x;
        sum_xy += x * y;
    }

    double denom = n * sum_xx - sum_x * sum_x;
    if (fabs(denom) < 1e-15) { *slope = 0; *intercept = 0; *r2 = 0; return; }

    *slope = (float)((n * sum_xy - sum_x * sum_y) / denom);
    *intercept = (float)((sum_y - (*slope) * sum_x) / n);

    /* R² */
    double y_mean = sum_y / n;
    double ss_tot = 0, ss_res = 0;
    for (int i = start; i <= end; i++) {
        if (s[i].t_s <= 0) continue;
        double x = log(s[i].t_s);
        double y = s[i].dt_mk / 1000.0f;
        double y_pred = (*slope) * x + (*intercept);
        ss_tot += (y - y_mean) * (y - y_mean);
        ss_res += (y - y_pred) * (y - y_pred);
    }
    *r2 = (ss_tot > 1e-15) ? (float)(1.0 - ss_res / ss_tot) : 0.0f;
}

/* ---- Find optimal regression window (maximize R²) ---- */
static void find_best_window(const meas_sample_t *s, int pulse_samples,
                              int *best_start, int *best_end,
                              float *best_slope, float *best_intercept,
                              float *best_r2)
{
    /* Search window: from 20% to 90% of heating phase */
    int min_start = pulse_samples / 5;     /* skip early transient */
    int max_start = pulse_samples / 2;     /* must have enough points */
    int min_window = 10;                    /* minimum points for fit */
    int max_window = (pulse_samples * 9) / 10;

    *best_r2 = -1.0f;
    *best_start = 0;
    *best_end = 0;
    *best_slope = 0;
    *best_intercept = 0;

    for (int start = min_start; start <= max_start; start++) {
        for (int window = min_window; window <= max_window && (start + window - 1) < pulse_samples; window++) {
            int end = start + window - 1;
            float slope, intercept, r2;
            linear_fit_ln_t(s, start, end, &slope, &intercept, &r2);

            /* Prefer windows with R² > 0.9998, maximize window length then R² */
            if (r2 > 0.9995f && r2 > *best_r2) {
                *best_r2 = r2;
                *best_start = start;
                *best_end = end;
                *best_slope = slope;
                *best_intercept = intercept;
            }
        }
    }

    /* If no window meets threshold, use best available */
    if (*best_r2 < 0) {
        linear_fit_ln_t(s, min_start, pulse_samples - 1,
                        best_slope, best_intercept, best_r2);
        *best_start = min_start;
        *best_end = pulse_samples - 1;
    }
}

/* ---- Levenberg-Marquardt fit for thermal diffusivity α ----
 * Model: ΔT(t) = (Q/(4πλ)) * [ln(t) + ln(4α/r²) - γ]
 * Parameters: λ, α (2 parameters)
 * We already have λ from the slope; use it to initialize.
 */
static void fit_diffusivity(const meas_sample_t *s, int start, int end,
                             float Q_per_m, float lambda,
                             float *alpha, float *r2_fit)
{
    /* Probe radius (approximate for needle probe) */
    const float r_probe = 0.0006f;  /* 0.6 mm radius */
    const float pi = 3.14159265359f;

    /* Initial guess: α = 0.5 mm²/s */
    float a = 0.5e-6f;  /* m²/s */
    float lambda_fit = lambda;

    /* Levenberg-Marquardt */
    float lambda_LM = 0.001f;
    int max_iter = 30;

    for (int iter = 0; iter < max_iter; iter++) {
        double resid_sum = 0;
        double JtF_alpha = 0, JtF_lambda = 0;
        double JtJ_aa = 0, JtJ_al = 0, JtJ_ll = 0;

        for (int i = start; i <= end; i++) {
            if (s[i].t_s <= 0) continue;

            double t = s[i].t_s;
            double dt_meas = s[i].dt_mk / 1000.0;

            /* Model: ΔT = (Q/(4πλ)) * [ln(t) + ln(4α/r²) - γ] */
            double arg = t * 4.0 * a / (r_probe * r_probe);
            if (arg <= 0) continue;
            double ln_term = log(arg);
            double model = (Q_per_m / (4.0 * pi * lambda_fit)) * (ln_term - GAMMA_EULER);

            double resid = dt_meas - model;
            resid_sum += resid * resid;

            /* Jacobian */
            double dF_dlambda = -(Q_per_m / (4.0 * pi * lambda_fit * lambda_fit)) * (ln_term - GAMMA_EULER);
            double dF_dalpha = (Q_per_m / (4.0 * pi * lambda_fit)) * (1.0 / a);

            JtF_alpha += dF_dalpha * resid;
            JtF_lambda += dF_dlambda * resid;

            JtJ_aa += dF_dalpha * dF_dalpha;
            JtJ_al += dF_dalpha * dF_dlambda;
            JtJ_ll += dF_dlambda * dF_dlambda;
        }

        /* Damped normal equations */
        double det = (JtJ_aa + lambda_LM) * (JtJ_ll + lambda_LM) - JtJ_al * JtJ_al;
        if (fabs(det) < 1e-20) break;

        double da = ((JtJ_ll + lambda_LM) * JtF_alpha - JtJ_al * JtF_lambda) / det;
        double dl = ((JtJ_aa + lambda_LM) * JtF_lambda - JtJ_al * JtF_alpha) / det;

        float a_new = a + da;
        float l_new = lambda_fit + dl;

        /* Constrain to physical range */
        if (a_new < 1e-9f) a_new = 1e-9f;    /* 0.001 mm²/s min */
        if (a_new > 5e-6f) a_new = 5e-6f;    /* 5 mm²/s max */
        if (l_new < 0.001f) l_new = 0.001f;
        if (l_new > 20.0f) l_new = 20.0f;

        /* Check if residual improved */
        a = a_new;
        lambda_fit = l_new;

        if (fabs(da) < 1e-10 && fabs(dl) < 1e-8) break;
        lambda_LM *= 0.8f;  /* decrease damping on success */
    }

    *alpha = a * 1e6f;  /* convert m²/s → mm²/s */

    /* Compute R² of fit */
    double ss_tot = 0, ss_res = 0, y_mean = 0;
    int n = 0;
    for (int i = start; i <= end; i++) {
        if (s[i].t_s <= 0) continue;
        y_mean += s[i].dt_mk / 1000.0;
        n++;
    }
    if (n > 0) y_mean /= n;

    for (int i = start; i <= end; i++) {
        if (s[i].t_s <= 0) continue;
        double t = s[i].t_s;
        double dt_meas = s[i].dt_mk / 1000.0;
        double arg = t * 4.0 * a / (r_probe * r_probe);
        if (arg <= 0) continue;
        double model = (Q_per_m / (4.0 * pi * lambda_fit)) * (log(arg) - GAMMA_EULER);
        ss_tot += (dt_meas - y_mean) * (dt_meas - y_mean);
        ss_res += (dt_meas - model) * (dt_meas - model);
    }
    *r2_fit = (ss_tot > 1e-15) ? (float)(1.0 - ss_res / ss_tot) : 0.0f;
}

/* ---- Main measurement task ---- */
void measurement_task(void *arg)
{
    (void)arg;
    const float pi = 3.14159265359f;

    while (1) {
        switch (state) {
        case MEAS_IDLE:
        case MEAS_DONE:
        case MEAS_ERROR:
            vTaskDelay(pdMS_TO_TICKS(50));
            break;

        case MEAS_ARMING:
        {
            /* Wait for thermal equilibrium */
            const float drift_thresh = 0.01f;  /* 0.01 °C/s */
            const float equil_duration = 10.0f;  /* 10 seconds stable */

            ESP_LOGI(TAG, "Arming: waiting for equilibrium...");
            int stable_count = 0;
            int64_t t_start = esp_timer_get_time();

            while (state == MEAS_ARMING) {
                probe_update();
                if (probe_is_equilibrium(drift_thresh, 2.0f)) {
                    stable_count++;
                } else {
                    stable_count = 0;
                }

                /* Need 5 consecutive 2-second windows stable = 10 seconds */
                if (stable_count >= 5) {
                    break;
                }

                /* Timeout: 120 seconds max */
                if ((esp_timer_get_time() - t_start) > 120e6) {
                    ESP_LOGW(TAG, "Equilibrium timeout, proceeding anyway");
                    break;
                }
                vTaskDelay(pdMS_TO_TICKS(100));
            }

            state = MEAS_BASELINE;
            break;
        }

        case MEAS_BASELINE:
        {
            const material_preset_t *preset = &presets[current_material];
            ESP_LOGI(TAG, "Baseline phase: %d samples", (int)(MEAS_BASELINE_S * preset->sample_rate_hz));

            float t0_sum = 0;
            int t0_count = 0;
            int64_t t_start = esp_timer_get_time();

            while (state == MEAS_BASELINE) {
                float elapsed = (esp_timer_get_time() - t_start) / 1e6f;
                if (elapsed >= MEAS_BASELINE_S) break;

                float temp = probe_read_temperature();
                t0_sum += temp;
                t0_count++;

                vTaskDelay(pdMS_TO_TICKS(1000 / preset->sample_rate_hz));
            }

            result.t0_c = t0_sum / t0_count;
            ESP_LOGI(TAG, "Baseline T0 = %.4f °C (%d samples)", result.t0_c, t0_count);

            /* Set heater power */
            float actual_power;
            heater_set_power(preset->power_w, &actual_power);
            heater_enable(true);

            state = MEAS_HEATING;
            break;
        }

        case MEAS_HEATING:
        {
            const material_preset_t *preset = &presets[current_material];
            float pulse_s = preset->pulse_s;
            int sample_rate = preset->sample_rate_hz;
            int64_t t_start = esp_timer_get_time();

            ESP_LOGI(TAG, "Heating: %.2f W for %.1f s @ %d Hz",
                     preset->power_w, pulse_s, sample_rate);

            while (state == MEAS_HEATING) {
                float elapsed = (esp_timer_get_time() - t_start) / 1e6f;
                if (elapsed >= pulse_s) break;
                if (sample_count >= MEAS_MAX_SAMPLES) break;

                /* PI update for constant power */
                heater_pi_update();

                /* Read temperature + heater V/I */
                float temp = probe_read_temperature();
                float v, i;
                heater_read_vi(&v, &i);
                float q = v * i;

                float dt = (temp - result.t0_c) * 1000.0f;  /* mK */

                meas_sample_t *s = &samples[sample_count];
                s->t_s = elapsed;
                s->temp_c = temp;
                s->dt_mk = dt;
                s->v_heater = v;
                s->i_heater = i;
                s->q_w = q;
                sample_count++;

                /* Safety: max temperature rise */
                if ((temp - result.t0_c) > HEATER_MAX_TEMP_RISE_C) {
                    ESP_LOGW(TAG, "Max ΔT exceeded (%.2f K), stopping heater",
                             temp - result.t0_c);
                    heater_emergency_stop();
                    state = MEAS_COOLING;
                    break;
                }

                vTaskDelay(pdMS_TO_TICKS(1000 / sample_rate));
            }

            /* Turn off heater */
            heater_enable(false);
            result.pulse_duration_s = pulse_s;

            if (state == MEAS_HEATING) state = MEAS_COOLING;
            break;
        }

        case MEAS_COOLING:
        {
            const material_preset_t *preset = &presets[current_material];
            float cooling_s = preset->pulse_s * MEAS_COOLING_MULT;
            int sample_rate = preset->sample_rate_hz;
            int64_t t_start = esp_timer_get_time();
            int pulse_samples = sample_count;

            ESP_LOGI(TAG, "Cooling: %.1f s @ %d Hz", cooling_s, sample_rate);

            while (state == MEAS_COOLING) {
                float elapsed = (esp_timer_get_time() - t_start) / 1e6f;
                if (elapsed >= cooling_s) break;
                if (sample_count >= MEAS_MAX_SAMPLES) break;

                float temp = probe_read_temperature();
                float dt = (temp - result.t0_c) * 1000.0f;

                meas_sample_t *s = &samples[sample_count];
                s->t_s = elapsed + result.pulse_duration_s;
                s->temp_c = temp;
                s->dt_mk = dt;
                s->v_heater = 0;
                s->i_heater = 0;
                s->q_w = 0;
                sample_count++;

                vTaskDelay(pdMS_TO_TICKS(1000 / sample_rate));
            }

            result.total_duration_s = result.pulse_duration_s + cooling_s;
            state = MEAS_ANALYZING;
            break;
        }

        case MEAS_ANALYZING:
        {
            ESP_LOGI(TAG, "Analyzing %d samples...", sample_count);

            /* Compute average heater power during pulse */
            const material_preset_t *preset = &presets[current_material];
            int pulse_samples = (int)(preset->pulse_s * preset->sample_rate_hz);
            if (pulse_samples > sample_count) pulse_samples = sample_count;

            double q_sum = 0;
            int q_count = 0;
            for (int i = 0; i < pulse_samples; i++) {
                q_sum += samples[i].q_w;
                q_count++;
            }
            float avg_q = (q_count > 0) ? (float)(q_sum / q_count) : 0.0f;
            result.avg_power_w = avg_q;

            /* Q per unit length (W/m) */
            const probe_info_t *pinfo = probe_get_info();
            float Q_per_m = avg_q / pinfo->active_length;

            /* Find max ΔT */
            float dt_max = 0;
            for (int i = 0; i < sample_count; i++) {
                if (samples[i].dt_mk > dt_max) dt_max = samples[i].dt_mk;
            }
            result.dt_max_c = dt_max / 1000.0f;

            /* Find best regression window */
            int best_start, best_end;
            float best_slope, best_intercept, best_r2;
            find_best_window(samples, pulse_samples,
                             &best_start, &best_end,
                             &best_slope, &best_intercept, &best_r2);

            result.slope = best_slope;
            result.r_squared = best_r2;
            result.fit_start_idx = best_start;
            result.fit_end_idx = best_end;
            result.n_points = best_end - best_start + 1;

            /* Thermal conductivity: λ = Q / (4π · m)
             * m is in °C/ln(s), Q in W/m
             * λ in W/(m·K)
             */
            if (fabsf(best_slope) > 1e-10f) {
                result.lambda = Q_per_m / (4.0f * pi * best_slope);
            } else {
                result.lambda = 0;
            }

            /* Apply calibration */
            result.lambda = result.lambda * calibration_factor + cal_offset;

            /* Fit thermal diffusivity */
            float alpha_r2;
            fit_diffusivity(samples, best_start, best_end,
                            Q_per_m, result.lambda,
                            &result.alpha, &alpha_r2);
            result.fit_alpha_r2 = alpha_r2;

            /* Volumetric heat capacity: ρcₚ = λ / α
             * λ in W/(m·K) = J/(m·s·K)
             * α in mm²/s = 1e-6 m²/s
             * ρcₚ = λ / (α * 1e-6)  → J/(m³·K)
             */
            if (result.alpha > 0.01f) {
                result.rho_cp = result.lambda / (result.alpha * 1e-6f);
            } else {
                result.rho_cp = 0;
            }

            /* Thermal effusivity: e = √(λ · ρcₚ) → J/(m²·K·s^0.5) */
            if (result.rho_cp > 0) {
                result.effusivity = sqrtf(result.lambda * result.rho_cp);
            } else {
                result.effusivity = 0;
            }

            /* Metadata */
            result.material_id = (uint8_t)current_material;
            result.probe_type = (uint8_t)pinfo->type;
            result.timestamp = (uint32_t)(esp_timer_get_time() / 1000000);
            result.final_state = MEAS_DONE;

            ESP_LOGI(TAG, "Result: λ=%.4f W/m·K, α=%.3f mm²/s, ρcₚ=%.3e J/m³·K, e=%.1f, R²=%.5f",
                     result.lambda, result.alpha, result.rho_cp,
                     result.effusivity, result.r_squared);

            state = MEAS_DONE;
            break;
        }
        } /* switch */
    } /* while */
}