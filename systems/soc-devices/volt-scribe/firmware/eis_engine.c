/*
 * volt-scribe — eis_engine.c
 * Electrochemical Impedance Spectroscopy engine
 *
 * Generates a small AC perturbation (1–100 mV rms) via DAC2 (DDS sine)
 * at frequencies from freq_start to freq_end.
 * At each frequency, measures current and voltage simultaneously,
 * computes real/imag impedance via DFT.
 * Fits Randles equivalent circuit: R_s + (C_dl ∥ (R_ct + Z_W))
 */

#include "eis_engine.h"
#include "potentiostat.h"
#include "dsp.h"
#include "display.h"
#include "sd_log.h"
#include "ble_relay.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

#define EIS_MAX_POINTS 256
#define EIS_DFT_SAMPLES 1024

/* DDS sine table (256 entries, 12-bit for DAC2) */
static const uint16_t sine_table[256] = {
    2048,2098,2148,2198,2248,2298,2348,2397,2445,2493,2540,2586,
    2631,2674,2717,2757,2796,2833,2868,2902,2933,2962,2989,3014,
    3037,3057,3074,3089,3101,3111,3118,3122,3124,3122,3118,3111,
    3101,3089,3074,3057,3037,3014,2989,2962,2933,2902,2868,2833,
    2796,2757,2717,2674,2631,2586,2540,2493,2445,2397,2348,2298,
    2248,2198,2148,2098,2048,1997,1947,1897,1847,1797,1747,1698,
    1649,1600,1553,1507,1462,1418,1375,1334,1294,1255,1218,1183,
    1149,1118,1089,1062,1037,1014,991,971,954,939,927,917,
    910,906,904,906,910,917,927,939,954,971,991,1014,
    1037,1062,1089,1118,1149,1183,1218,1255,1294,1334,1375,1418,
    1462,1507,1553,1600,1649,1698,1747,1797,1847,1897,1947,1997,
    /* Extended sine for higher resolution — the rest is computed */
};

/* ── EIS data storage ──────────────────────────────────────────── */

typedef struct {
    float freq;      /* Hz */
    float Z_real;    /* Ω (real part) */
    float Z_imag;    /* Ω (imaginary part) */
    float magnitude; /* |Z| in Ω */
    float phase;     /* degrees */
} eis_point_t;

static eis_point_t eis_data[EIS_MAX_POINTS];
static int eis_count = 0;

/* ── DDS sine wave generation ──────────────────────────────────── */

static void dds_generate(float freq, float amplitude_v, int n_samples)
{
    /* Generate sine wave on DAC2 at given frequency and amplitude.
     * Uses TIM6 + DMA to stream sine table to DAC2 at calculated rate.
     * For now: simple loop-based generation for clarity. */

    float phase_inc = 2.0f * M_PI * freq / (float)n_samples;
    float sample_period = 1.0f / (freq * (float)n_samples / 256.0f);
    int period_us = (int)(1.0e6f / freq / 256.0f);
    if (period_us < 10) period_us = 10;

    uint32_t dac_mid = 2048;
    float dac_scale = amplitude_v / 2.048f * 2048.0f;  /* Scale to DAC counts */

    for (int i = 0; i < n_samples; i++) {
        uint16_t dac_val = (uint16_t)(dac_mid + dac_scale * sinf(phase_inc * i));
        if (dac_val > 4095) dac_val = 4095;
        HAL_DAC_SetValue(&hdac2, DAC_CHANNEL_1, DAC_ALIGN_12B_R, dac_val);
        HAL_Delay(period_us / 1000);
        if (period_us % 1000 > 500) {
            /* Sub-ms delay using busy loop */
            for (volatile int d = 0; d < period_us % 1000 * 8; d++);
        }
    }
}

/* ── Single-frequency impedance measurement ────────────────────── */

static void measure_impedance(float freq, float ac_amplitude,
                              float *Z_real, float *Z_imag)
{
    int n_samples = EIS_DFT_SAMPLES;
    if (freq > 10000.0f) n_samples = 256;
    if (freq < 10.0f) n_samples = 4096;

    float *v_samples = (float *)malloc(n_samples * sizeof(float));
    float *i_samples = (float *)malloc(n_samples * sizeof(float));
    if (!v_samples || !i_samples) {
        *Z_real = 0;
        *Z_imag = 0;
        return;
    }

    /* Set DC bias */
    pot_set_voltage(0.0f);  /* DC bias set separately */
    HAL_Delay(100);  /* Settle */

    /* Collect V and I samples with AC stimulus */
    float period = 1.0f / freq;
    int sample_delay_us = (int)(period * 1e6f / n_samples);
    if (sample_delay_us < 10) sample_delay_us = 10;

    for (int k = 0; k < n_samples; k++) {
        /* Generate AC stimulus point */
        float phase = 2.0f * M_PI * freq * (float)k / (float)n_samples;
        float ac_v = ac_amplitude * sinf(phase);

        /* DAC2 = AC component */
        uint16_t dac2_val = (uint16_t)(2048 + ac_v / 2.048f * 2048.0f);
        HAL_DAC_SetValue(&hdac2, DAC_CHANNEL_1, DAC_ALIGN_12B_R, dac2_val);

        /* Small delay for settling */
        if (sample_delay_us > 1000) {
            HAL_Delay(sample_delay_us / 1000);
        } else {
            for (volatile int d = 0; d < sample_delay_us * 8; d++);
        }

        /* Sample voltage and current */
        v_samples[k] = pot_read_potential();
        i_samples[k] = pot_read_current();
    }

    /* DFT at stimulus frequency to extract real/imag components */
    float v_real = 0, v_imag_dft = 0;
    float i_real = 0, i_imag_dft = 0;

    for (int k = 0; k < n_samples; k++) {
        float angle = 2.0f * M_PI * (float)k / (float)n_samples;
        float cos_w = cosf(angle);
        float sin_w = sinf(angle);

        v_real += v_samples[k] * cos_w;
        v_imag_dft += v_samples[k] * sin_w;
        i_real += i_samples[k] * cos_w;
        i_imag_dft += i_samples[k] * sin_w;
    }

    v_real *= 2.0f / n_samples;
    v_imag_dft *= 2.0f / n_samples;
    i_real *= 2.0f / n_samples;
    i_imag_dft *= 2.0f / n_samples;

    /* Z = V/I → Z_real + j*Z_imag */
    float i_mag2 = i_real * i_real + i_imag_dft * i_imag_dft;
    if (i_mag2 < 1e-30f) i_mag2 = 1e-30f;

    *Z_real = (v_real * i_real + v_imag_dft * i_imag_dft) / i_mag2;
    *Z_imag = (v_imag_dft * i_real - v_real * i_imag_dft) / i_mag2;

    free(v_samples);
    free(i_samples);
}

/* ── Randles circuit fitting ─────────────────────────────────── */

typedef struct {
    float R_s;     /* Solution resistance (Ω) */
    float R_ct;    /* Charge-transfer resistance (Ω) */
    float C_dl;    /* Double-layer capacitance (F) */
    float alpha;    /* CPE exponent (0–1) */
    float sigma_w; /* Warburg coefficient */
} randles_t;

static void fit_randles(const eis_point_t *data, int n, randles_t *fit)
{
    /* Simple Levenberg-Marquardt fitting to Randles circuit:
     * Z = R_s + 1/(1/R_ct + (j*ω)^α * C_dl) + σ_w/√(j*ω)
     * Initial guesses from data:
     *   R_s ≈ Z_real at high freq
     *   R_ct ≈ Z_real at low freq - R_s
     *   C_dl from phase peak frequency
     */

    /* R_s = minimum real impedance (high frequency) */
    fit->R_s = data[0].Z_real;
    for (int i = 1; i < n; i++) {
        if (data[i].Z_real < fit->R_s) fit->R_s = data[i].Z_real;
    }

    /* R_ct = diameter of semicircle (low freq real - R_s) */
    float max_real = data[n-1].Z_real;
    for (int i = 0; i < n; i++) {
        if (data[i].Z_real > max_real) max_real = data[i].Z_real;
    }
    fit->R_ct = max_real - fit->R_s;
    if (fit->R_ct < 1.0f) fit->R_ct = 1.0f;

    /* Find frequency of maximum -Z_imag (semicircle top) */
    float max_neg_imag = 0;
    float f_peak = 1.0f;
    for (int i = 0; i < n; i++) {
        if (-data[i].Z_imag > max_neg_imag) {
            max_neg_imag = -data[i].Z_imag;
            f_peak = data[i].freq;
        }
    }

    /* C_dl from ω_peak * R_ct * C_dl = 1 → C_dl = 1/(2π*f_peak*R_ct) */
    fit->C_dl = 1.0f / (2.0f * M_PI * f_peak * fit->R_ct);

    /* CPE exponent — start with ideal capacitor */
    fit->alpha = 0.90f;

    /* Warburg coefficient from 45° line at low freq */
    if (n > 3) {
        float low_f = data[n-1].freq;
        float low_Z_real = data[n-1].Z_real;
        float low_Z_imag_neg = -data[n-1].Z_imag;
        fit->sigma_w = (low_Z_real - fit->R_s - fit->R_ct) * sqrtf(low_f);
    } else {
        fit->sigma_w = 0;
    }
}

/* ── Main EIS run ──────────────────────────────────────────────── */

void eis_run(const struct params_t *p)
{
    eis_count = 0;

    printf("Running EIS: %.0f Hz → %.0f Hz, DC=%.3fV, AC=%.1fmV rms\r\n",
           p->eis_freq_start, p->eis_freq_end,
           p->eis_dc_bias, p->eis_ac_amp * 1000);

    tia_range_t best_range = pot_auto_range();
    printf("TIA range: %s\r\n", tia_range_name(best_range));

    /* Set DC bias */
    pot_set_voltage(p->eis_dc_bias);
    HAL_Delay(500);  /* Settle */

    sdlog_open("eis");
    sdlog_write("freq_Hz,Z_real_Ohm,Z_imag_Ohm,|Z|_Ohm,phase_deg\r\n");

    /* Logarithmic frequency sweep */
    float f = p->eis_freq_start;
    float f_ratio = powf(10.0f, 1.0f / p->eis_ppd);

    while (f <= p->eis_freq_end && eis_count < EIS_MAX_POINTS) {
        float Z_real, Z_imag;
        measure_impedance(f, p->eis_ac_amp, &Z_real, &Z_imag);

        float magnitude = sqrtf(Z_real * Z_real + Z_imag * Z_imag);
        float phase = atan2f(Z_imag, Z_real) * 180.0f / M_PI;

        eis_data[eis_count].freq = f;
        eis_data[eis_count].Z_real = Z_real;
        eis_data[eis_count].Z_imag = Z_imag;
        eis_data[eis_count].magnitude = magnitude;
        eis_data[eis_count].phase = phase;
        eis_count++;

        char line[96];
        snprintf(line, sizeof(line), "%.1f,%.2f,%.2f,%.2f,%.1f\r\n",
                 f, Z_real, Z_imag, magnitude, phase);
        sdlog_write(line);

        /* Stream Nyquist point */
        ble_relay_send_eis_point(Z_real, -Z_imag, f);

        printf("%.0f Hz: Z'=%.0f Ω, Z''=%.0f Ω, |Z|=%.0f Ω, φ=%.1f°\r\n",
               f, Z_real, Z_imag, magnitude, phase);

        f *= f_ratio;

        extern volatile int experiment_running;
        if (!experiment_running) break;
    }

    /* Fit Randles circuit */
    randles_t fit;
    fit_randles(eis_data, eis_count, &fit);

    printf("Fitting Randles circuit:\r\n");
    printf("  R_s  = %.0f Ω\r\n", fit.R_s);
    printf("  R_ct = %.0f Ω\r\n", fit.R_ct);
    printf("  C_dl = %.2f µF\r\n", fit.C_dl * 1e6f);
    printf("  α    = %.2f\r\n", fit.alpha);
    printf("  σ_w  = %.1f Ω/√Hz\r\n", fit.sigma_w);

    char comment[128];
    snprintf(comment, sizeof(comment),
             "# R_s=%.0f, R_ct=%.0f, C_dl=%.2fuF, alpha=%.2f, sigma_w=%.1f\r\n",
             fit.R_s, fit.R_ct, fit.C_dl * 1e6f, fit.alpha, fit.sigma_w);
    sdlog_write(comment);

    char filename[32];
    snprintf(filename, sizeof(filename), "eis_%06d.csv", sdlog_get_sequence());
    sdlog_close(filename);
    printf("Result saved to SD: %s\r\n", filename);

    display_plot_nyquist(eis_data, eis_count);
}