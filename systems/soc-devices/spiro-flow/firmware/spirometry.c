/**
 * spiro_flow/spirometry.c — Spirometry parameter computation
 *
 * Computes FVC, FEV1, PEF, FEF25-75, FEV1/FVC, FET, PIF, FIVC
 * from a flow-vs-time maneuver buffer. Applies BTPS correction,
 * back-extrapolation, and ATS/ERS 2019 acceptability grading.
 *
 * Reference equations: ECSC/ERS 1993 predicted values.
 */

#include "main.h"
#include "spirometry.h"
#include <math.h>
#include <string.h>

#define TAG "SPIRO"

/* ── BTPS correction ───────────────────────────────────────────────── */

float compute_btps(float temp_c, float pressure_mmhg, float humidity_pct)
{
    /* BTPS factor = (310.15 / (T_amb + 273.15)) × (Pb - PH2O) / (Pb - 47)
     *
     * T_amb: ambient temperature in °C
     * Pb: barometric pressure in mmHg
     * PH2O: water vapor pressure at ambient temp (from humidity)
     *
     * Water vapor pressure (Antoine equation):
     *   PH2O = 10^(8.07131 - 1730.63/(233.426 + T_c))  [mmHg]
     * Then multiply by relative humidity fraction.
     */
    float T_K = temp_c + 273.15f;
    float antoine = 8.07131f - 1730.63f / (233.426f + temp_c);
    float PH2O_ambient = powf(10.0f, antoine) * (humidity_pct / 100.0f);

    float btps = (BTPS_BODY_TEMP_K / T_K) *
                 (pressure_mmhg - PH2O_ambient) /
                 (pressure_mmhg - BTPS_WATER_VAPOR_MMHG);

    /* Sanity clamp: typical range 1.01 – 1.10 */
    if (btps < 0.95f) btps = 0.95f;
    if (btps > 1.15f) btps = 1.15f;

    return btps;
}

/* ── Back-extrapolation ────────────────────────────────────────────── */

/* Find the true time zero by back-extrapolating the volume-time curve.
 * The point where the steepest part of the volume curve intersects
 * zero volume is the true start of the maneuver.
 *
 * Method: find the steepest 80ms segment of the volume-time curve,
 * extrapolate backward to V=0. The time offset = back-extrapolated volume.
 */
static float back_extrapolate(const maneuver_buffer_t *m, int *zero_index)
{
    if (m->n_samples < 20) {
        *zero_index = 0;
        return 0.0f;
    }

    /* Find steepest 80ms segment (20 samples at 250 Hz) */
    float max_slope = 0;
    int max_slope_idx = 0;

    for (int i = 20; i < m->n_samples - 20; i++) {
        float dv = m->volume_ml[i+20] - m->volume_ml[i-20];
        /* slope in mL/s over 40-sample window (160ms) */
        float slope = dv / (40.0f / SAMPLE_RATE_HZ);
        if (slope > max_slope) {
            max_slope = slope;
            max_slope_idx = i;
        }
    }

    /* Linear extrapolation from steepest point back to V=0 */
    float v_at_peak = m->volume_ml[max_slope_idx];
    float dt_to_peak = (float)max_slope_idx / SAMPLE_RATE_HZ;

    /* V = slope * (t - t_zero) → t_zero = t_peak - V_peak/slope */
    if (max_slope < 1.0f) {
        *zero_index = 0;
        return 0.0f;
    }

    float t_zero_offset = v_at_peak / max_slope; /* seconds */
    float bev_ml = max_slope * t_zero_offset - v_at_peak;

    /* Actually BEV is the volume at the extrapolated time zero
     * of the actual curve. Simpler: BEV = volume at sample 0
     * minus extrapolated volume at sample 0.
     * For a well-started maneuver, BEV should be small.
     */
    /* BEV = V_extrapolated(t=0) = V_peak - slope * t_peak
     * But our volume[0] is already ~0, so BEV is the difference
     * between the extrapolated start and actual start.
     */
    float v_extrapolated_at_0 = v_at_peak - max_slope * dt_to_peak;
    bev_ml = fabsf(v_extrapolated_at_0 - m->volume_ml[0]);

    *zero_index = max_slope_idx - (int)(t_zero_offset * SAMPLE_RATE_HZ);
    if (*zero_index < 0) *zero_index = 0;

    return bev_ml;
}

/* ── Predicted values (ECSC/ERS 1993) ──────────────────────────────── */

void compute_predicted(const patient_t *p,
                        float *fev1_pred, float *fvc_pred,
                        float *fev1_fvc_pred, float *lln_ratio)
{
    float height_m = (float)p->height_cm / 100.0f;
    float age = (float)p->age_years;

    /* ECSC/ERS 1993 reference equations */
    if (p->sex == 0) {
        /* Male */
        *fev1_pred  = 4.30f * height_m - 0.029f * age - 2.89f;
        *fvc_pred   = 5.76f * height_m - 0.026f * age - 4.34f;
    } else {
        /* Female */
        *fev1_pred  = 3.95f * height_m - 0.022f * age - 2.60f;
        *fvc_pred   = 4.43f * height_m - 0.026f * age - 2.89f;
    }

    /* Ethnicity correction */
    if (p->ethnicity == 1) {
        /* African descent: ~12% lower */
        *fev1_pred *= 0.88f;
        *fvc_pred  *= 0.88f;
    } else if (p->ethnicity == 2) {
        /* Asian: ~5% lower */
        *fev1_pred *= 0.95f;
        *fvc_pred  *= 0.95f;
    }

    /* FEV1/FVC predicted ~ 75-85% depending on age */
    if (*fvc_pred > 0.01f) {
        *fev1_fvc_pred = (*fev1_pred / *fvc_pred) * 100.0f;
    } else {
        *fev1_fvc_pred = 80.0f;
    }

    /* Lower Limit of Normal for FEV1/FVC (approximate, -8% from predicted) */
    *lln_ratio = *fev1_fvc_pred - 8.0f;

    /* Sanity: predicted values should be positive */
    if (*fev1_pred < 0.5f) *fev1_pred = 0.5f;
    if (*fvc_pred < 0.5f)  *fvc_pred = 0.5f;
}

/* ── Main spirometry computation ───────────────────────────────────── */

void spirometry_compute(maneuver_buffer_t *m, const patient_t *p,
                         const float *ambient, spiro_result_t *r)
{
    memset(r, 0, sizeof(spiro_result_t));
    r->valid = false;

    if (m->n_samples < 50) {
        ESP_LOGE(TAG, "Too few samples (%d) for spirometry", m->n_samples);
        return;
    }

    /* Ambient conditions */
    float temp_c = ambient[0];
    float pressure_mmhg = ambient[1];
    float humidity_pct = ambient[2];

    /* BTPS correction */
    float btps = compute_btps(temp_c, pressure_mmhg, humidity_pct);
    r->btps_factor = btps;
    r->ambient_temp_c = temp_c;
    r->ambient_pressure_mmhg = pressure_mmhg;
    r->ambient_humidity_pct = humidity_pct;

    /* Back-extrapolation to find true time zero */
    int zero_idx = 0;
    float bev_ml = back_extrapolate(m, &zero_idx);
    r->back_extrap_ml = bev_ml;

    ESP_LOGI(TAG, "BTPS factor: %.3f, BEV: %.1f mL, zero_idx: %d",
             btps, bev_ml, zero_idx);

    /* Shift volume array so true zero is at index 0 */
    /* (In practice, we just offset all time calculations by zero_idx) */

    int n = m->n_samples - zero_idx;
    if (n < 30) {
        ESP_LOGE(TAG, "Effective samples after BEV too small");
        return;
    }

    /* Apply BTPS correction to volume and flow */
    /* We work with corrected values from here on */
    float vol_corrected[MAX_SAMPLES];
    float flow_corrected[MAX_SAMPLES];
    for (int i = 0; i < n && i < MAX_SAMPLES; i++) {
        vol_corrected[i] = m->volume_ml[zero_idx + i] * btps;
        flow_corrected[i] = m->flow_lps[zero_idx + i] * btps;
    }

    /* FVC = total expired volume (max volume reached) */
    float max_vol_ml = 0;
    int max_vol_idx = 0;
    for (int i = 0; i < n; i++) {
        if (vol_corrected[i] > max_vol_ml) {
            max_vol_ml = vol_corrected[i];
            max_vol_idx = i;
        }
    }
    r->fvc_liters = max_vol_ml / 1000.0f;

    /* FEV1 = volume expired in first 1 second */
    /* Find volume at t=1.0s from zero_idx */
    int t1_idx = (int)(1.0f * SAMPLE_RATE_HZ);  /* 250 samples = 1s */
    if (t1_idx < n) {
        r->fev1_liters = vol_corrected[t1_idx] / 1000.0f;
    } else {
        r->fev1_liters = vol_corrected[n-1] / 1000.0f; /* less than 1s */
    }

    /* FEV1/FVC ratio */
    if (r->fvc_liters > 0.01f) {
        r->fev1_fvc_ratio = (r->fev1_liters / r->fvc_liters) * 100.0f;
    } else {
        r->fev1_fvc_ratio = 0;
    }

    /* PEF = peak expiratory flow (max flow during expiration) */
    float max_flow = 0;
    int max_flow_idx = 0;
    for (int i = 0; i < n && i < max_vol_idx; i++) {
        if (flow_corrected[i] > max_flow) {
            max_flow = flow_corrected[i];
            max_flow_idx = i;
        }
    }
    r->pef_lps = max_flow;

    /* Time to PEF (PEFT) */
    r->peft_ms = (uint16_t)((float)max_flow_idx / SAMPLE_RATE_HZ * 1000.0f);

    /* FEF25-75% = mean flow between 25% and 75% of FVC */
    float v25 = max_vol_ml * 0.25f;
    float v75 = max_vol_ml * 0.75f;
    int i25 = 0, i75 = 0;
    for (int i = 0; i < n; i++) {
        if (vol_corrected[i] >= v25 && i25 == 0) i25 = i;
        if (vol_corrected[i] >= v75 && i75 == 0) i75 = i;
    }
    if (i75 > i25) {
        float dt_2575 = (float)(i75 - i25) / SAMPLE_RATE_HZ;
        float dv_2575 = (v75 - v25) / 1000.0f; /* L */
        r->fef2575_lps = dv_2575 / dt_2575;
    } else {
        r->fef2575_lps = 0;
    }

    /* FET = forced expiratory time (from zero to end of maneuver) */
    r->fet_sec = (float)n / SAMPLE_RATE_HZ;

    /* PIF = peak inspiratory flow (max negative flow after FVC) */
    float max_inspiratory = 0;
    for (int i = max_vol_idx; i < n; i++) {
        if (-flow_corrected[i] > max_inspiratory) {
            max_inspiratory = -flow_corrected[i];
        }
    }
    r->pif_lps = max_inspiratory;

    /* FIVC = inspired volume after FVC */
    float min_vol_after_peak = max_vol_ml;
    for (int i = max_vol_idx; i < n; i++) {
        if (vol_corrected[i] < min_vol_after_peak) {
            min_vol_after_peak = vol_corrected[i];
        }
    }
    r->fivc_liters = (max_vol_ml - min_vol_after_peak) / 1000.0f;

    /* Predicted values */
    float fev1_pred, fvc_pred, fev1_fvc_pred, lln;
    compute_predicted(p, &fev1_pred, &fvc_pred, &fev1_fvc_pred, &lln);
    r->fev1_pred = fev1_pred;
    r->fvc_pred = fvc_pred;
    r->fev1_fvc_pred = fev1_fvc_pred;
    r->lln_fev1_fvc = lln;

    /* Percent predicted */
    if (fev1_pred > 0.01f)
        r->fev1_pct_pred = (r->fev1_liters / fev1_pred) * 100.0f;
    if (fvc_pred > 0.01f)
        r->fvc_pct_pred = (r->fvc_liters / fvc_pred) * 100.0f;

    /* Diagnostic classification:
     * - Obstructive: FEV1/FVC < LLN (or < 70% as fixed ratio)
     * - Restrictive: FEV1/FVC ≥ LLN but FVC < 80% predicted
     * - Mixed: FEV1/FVC < LLN and FVC < 80% predicted
     * - Normal: FEV1/FVC ≥ LLN and FVC ≥ 80% predicted
     */
    if (r->fev1_fvc_ratio < lln) {
        if (r->fvc_pct_pred < 80.0f) {
            r->pattern = 3;  /* mixed obstructive + restrictive */
        } else {
            r->pattern = 1;  /* obstructive */
        }
    } else {
        if (r->fvc_pct_pred < 80.0f) {
            r->pattern = 2;  /* restrictive */
        } else {
            r->pattern = 0;  /* normal */
        }
    }

    /* Quality grading per ATS/ERS 2019 */
    r->grade = grade_maneuver(m, r);

    r->valid = true;

    ESP_LOGI(TAG, "FVC: %.2fL  FEV1: %.2fL  FEV1/FVC: %.1f%%  PEF: %.1fL/s  "
             "FEF25-75: %.1fL/s  FET: %.1fs  Grade: %c",
             r->fvc_liters, r->fev1_liters, r->fev1_fvc_ratio,
             r->pef_lps, r->fef2575_lps, r->fet_sec,
             'A' + (4 - r->grade));
}

/* ── Quality grading (ATS/ERS 2019) ────────────────────────────────── */

quality_grade_t grade_maneuver(const maneuver_buffer_t *m, const spiro_result_t *r)
{
    int score = 0;
    uint8_t flags = 0;

    /* Back-extrapolation volume */
    if (r->back_extrap_ml <= GRADE_A_BEV_ML) {
        score += 2;
        flags |= 0x01;
    } else if (r->back_extrap_ml <= GRADE_B_BEV_ML) {
        score += 1;
        flags |= 0x01;
    } else if (r->back_extrap_ml <= GRADE_C_BEV_ML) {
        score += 0;
        flags |= 0x01;
    } else {
        score -= 2;  /* unacceptable BEV */
    }

    /* Forced expiratory time */
    if (r->fet_sec >= GRADE_A_FET_SEC) {
        score += 2;
        flags |= 0x02;
    } else if (r->fet_sec >= GRADE_B_FET_SEC) {
        score += 1;
        flags |= 0x02;
    } else {
        score -= 1;
    }

    /* Smoothness: check for artifacts (sudden flow reversals) */
    /* Count zero-crossings in the flow curve after PEF */
    int zero_crossings = 0;
    int max_vol_idx = 0;
    float max_vol = 0;
    for (int i = 0; i < m->n_samples; i++) {
        if (m->volume_ml[i] > max_vol) {
            max_vol = m->volume_ml[i];
            max_vol_idx = i;
        }
    }
    for (int i = max_vol_idx + 10; i < m->n_samples - 1; i++) {
        if ((m->flow_lps[i] > 0.02f && m->flow_lps[i+1] < -0.02f) ||
            (m->flow_lps[i] < -0.02f && m->flow_lps[i+1] > 0.02f)) {
            zero_crossings++;
        }
    }
    if (zero_crossings <= 2) {
        score += 2;
        flags |= 0x04;
    } else if (zero_crossings <= 5) {
        score += 1;
        flags |= 0x04;
    } else {
        score -= 1;
    }

    /* Minimum volume check */
    if (r->fvc_liters * 1000.0f < MANEUVER_MIN_VOL_ML) {
        return GRADE_F;  /* too small */
    }

    r->acceptability_flags = flags;

    /* Map score to grade */
    if (score >= 6)  return GRADE_A;
    if (score >= 4)  return GRADE_B;
    if (score >= 2)  return GRADE_C;
    if (score >= 0)  return GRADE_D;
    return GRADE_F;
}