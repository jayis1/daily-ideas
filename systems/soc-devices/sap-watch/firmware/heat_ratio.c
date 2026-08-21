/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * heat_ratio.c — Heat-ratio method sap-flow velocity computation
 *                with wounding correction and zero-flow calibration
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "heat_ratio.h"
#include "probe.h"
#include <math.h>

/* ---- Module state ---- */
static float zero_flow_offset = 0.0f;       /* V_h at zero flow (predawn) */
static int   zero_cal_valid = 0;
static float wound_factor = WOUND_FACTOR_DEFAULT;
static float k_xylem = K_XYLEM_DEFAULT;
static float sapwood_area = SAPWOOD_AREA_DEFAULT_CM2;

/* History for drought-stress detection */
static float predawn_flux_history[STRESS_HISTORY_DAYS];
static int    predawn_history_count = 0;
static int    predawn_history_idx = 0;

/* ---- Public setters (called from LoRaWAN downlink) ---- */

void heat_ratio_set_wound_factor(float f)
{
    if (f > 0.5f && f < 3.0f)
        wound_factor = f;
}

void heat_ratio_set_sapwood_area(float area_cm2)
{
    if (area_cm2 > 1.0f && area_cm2 < 10000.0f)
        sapwood_area = area_cm2;
}

void heat_ratio_set_k_xylem(float k)
{
    if (k > 0.0005f && k < 0.01f)
        k_xylem = k;
}

float heat_ratio_get_sapwood_area(void) { return sapwood_area; }
float heat_ratio_get_wound_factor(void) { return wound_factor; }
int   heat_ratio_is_zero_cal_valid(void) { return zero_cal_valid; }

/*
 * Compute sap-flux velocity from a probe measurement result.
 *
 * The heat-ratio method (Burgess et al. 2001):
 *   V_h = (k / (x_up + x_dn)) × ln(dt_dn / dt_up)
 *
 * where:
 *   k       = thermal diffusivity of sapwood (cm²/s)
 *   x_up    = upstream probe spacing (5 mm = 0.5 cm)
 *   x_dn    = downstream probe spacing (10 mm = 1.0 cm)
 *   dt_up   = temperature rise at upstream thermistor (°C)
 *   dt_dn   = temperature rise at downstream thermistor (°C)
 *
 * When sap flows upward, heat is carried downstream → dt_dn > dt_up → ln > 0.
 * When sap flows downward (night root pressure), dt_up > dt_dn → ln < 0.
 *
 * Returns sap-flux velocity in cm/h, or NAN on error.
 */
float heat_ratio_compute_velocity(const probe_result_t *r)
{
    /* Validate temperature rises */
    if (r->dt_up <= 0.001f || r->dt_dn <= 0.001f) {
        /* Signal too small — either no pulse or thermistor disconnected */
        return NAN;
    }

    /* Heat-pulse velocity (cm/s) */
    float spacing = PROBE_SPACING_UP_MM + PROBE_SPACING_DN_MM;  /* 15 mm = 1.5 cm */
    float ratio = r->dt_dn / r->dt_up;
    if (ratio <= 0.0f)
        return NAN;

    float v_h = (k_xylem / (spacing * 0.1f)) * logf(ratio);  /* cm/s */

    /* Subtract zero-flow offset */
    v_h -= zero_flow_offset;

    /* Apply wound correction (Green et al. 2003) */
    v_h *= wound_factor;

    /* Convert heat-pulse velocity to sap-flux velocity:
     * V_sap = V_h × (ρ_w × c_w) / (ρ_s × c_s)
     * (simplification — full Swanson & Whitfield 1981 correction
     *  uses measured sapwood properties; we use defaults configurable
     *  via downlink)
     */
    float thermal_ratio = (RHO_WATER * C_WATER) / (RHO_SAPWOOD_DEFAULT * C_SAPWOOD_DEFAULT);
    float v_sap = v_h * thermal_ratio;  /* cm/s */

    /* Convert cm/s to cm/h */
    v_sap *= 3600.0f;

    return v_sap;
}

/*
 * Zero-flow calibration.
 * Called during predawn (transpiration ≈ 0). Collects multiple measurements
 * and averages the heat-pulse velocity to establish the zero offset.
 *
 * At zero flow, dt_up == dt_dn → ratio == 1.0 → ln(1) == 0 → V_h == 0.
 * In practice, imperfect probe installation causes a small offset.
 */
void heat_ratio_run_zero_calibration(const probe_result_t *results, int count)
{
    if (count < ZERO_CAL_MIN_SAMPLES)
        return;

    float sum = 0.0f;
    int valid = 0;
    float spacing = (PROBE_SPACING_UP_MM + PROBE_SPACING_DN_MM) * 0.1f;

    for (int i = 0; i < count; i++) {
        if (results[i].dt_up <= 0.001f || results[i].dt_dn <= 0.001f)
            continue;
        float ratio = results[i].dt_dn / results[i].dt_up;
        if (ratio <= 0.0f)
            continue;
        float v_h = (k_xylem / spacing) * logf(ratio);
        sum += v_h;
        valid++;
    }

    if (valid >= ZERO_CAL_MIN_SAMPLES / 2) {
        zero_flow_offset = sum / valid;
        zero_cal_valid = 1;
    }
}

void heat_ratio_invalidate_zero_cal(void)
{
    zero_cal_valid = 0;
}

/*
 * Convert sap-flux velocity (cm/h) to whole-tree water use (L/h).
 *
 * Q (L/h) = V_sap (cm/h) × A_sapwood (cm²) × 0.001
 */
float heat_ratio_velocity_to_flow(float v_sap_cmh)
{
    return v_sap_cmh * sapwood_area * 0.001f;
}

/*
 * Integrate sap flow over time using the trapezoidal rule.
 * samples[]: sap flow (L/h) at uniform time intervals
 * interval_h: time between samples (hours)
 * Returns total water use in litres.
 */
float heat_ratio_integrate_transpiration(const float *samples, int n, float interval_h)
{
    if (n < 2)
        return 0.0f;

    float total = 0.0f;
    for (int i = 1; i < n; i++) {
        total += (samples[i] + samples[i - 1]) * 0.5f * interval_h;
    }
    return total;
}

/*
 * Record a predawn flux value for the rolling baseline.
 * Called once per day at the predawn hour.
 */
void heat_ratio_record_predawn(float flux_cmh)
{
    if (flux_cmh < 0.0f)
        return;  /* negative = reverse flow, skip */

    predawn_flux_history[predawn_history_idx] = flux_cmh;
    predawn_history_idx = (predawn_history_idx + 1) % STRESS_HISTORY_DAYS;
    if (predawn_history_count < STRESS_HISTORY_DAYS)
        predawn_history_count++;
}

/*
 * Compute the 7-day rolling average predawn flux (baseline).
 */
float heat_ratio_predawn_baseline(void)
{
    if (predawn_history_count == 0)
        return NAN;

    float sum = 0.0f;
    for (int i = 0; i < predawn_history_count; i++)
        sum += predawn_flux_history[i];
    return sum / predawn_history_count;
}

/*
 * Drought-stress detection.
 * Compares today's midday flux to the 7-day predawn baseline.
 * If midday flux < STRESS_RATIO_THRESHOLD × predawn baseline,
 * the tree is closing stomata → water stress.
 *
 * Returns 1 if stress detected, 0 otherwise.
 */
int heat_ratio_detect_drought_stress(float midday_flux_cmh)
{
    if (midday_flux_cmh < STRESS_MIN_FLUX_CMH)
        return 0;  /* flux too low for reliable comparison */

    float baseline = heat_ratio_predawn_baseline();
    if (isnan(baseline) || baseline < STRESS_MIN_FLUX_CMH)
        return 0;

    float ratio = midday_flux_cmh / baseline;
    if (ratio < STRESS_RATIO_THRESHOLD)
        return 1;

    /* Also check: 30% drop from 7-day mean */
    if (midday_flux_cmh < baseline * (1.0f - STRESS_BASELINE_DROP_PCT / 100.0f))
        return 1;

    return 0;
}

/*
 * Compute vapor pressure deficit (VPD) from air temperature and RH.
 * VPD = SVP(T) × (1 - RH/100)
 * where SVP (saturation vapor pressure) uses the Tetens formula:
 *   SVP = 0.6108 × exp(17.27 × T / (T + 237.3))   [kPa, T in °C]
 */
float heat_ratio_compute_vpd(float air_temp_c, float rh_pct)
{
    float svp = 0.6108f * expf(17.27f * air_temp_c / (air_temp_c + 237.3f));
    float vpd = svp * (1.0f - rh_pct / 100.0f);
    return vpd;  /* kPa */
}