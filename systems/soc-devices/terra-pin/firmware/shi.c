/**
 * terra_pin/shi.c — Soil Health Index computation
 *
 * Fuses 5 soil parameters into a single 0–100 index using weighted
 * bell-curve sub-scores against agronomically optimal ranges.
 *
 * SHI = 30·S_resp + 25·S_redox + 20·S_ec + 15·S_moist + 10·S_temp
 *
 * Each sub-score is 0.0–1.0, computed via a bell-curve (triangular)
 * function centered on the optimal peak value.
 */

#include "main.h"
#include "esp_log.h"
#include <math.h>

static const char *TAG = "SHI";

/**
 * Triangular bell-curve score.
 * Returns 1.0 at peak, linearly decreasing to 0.0 at min and max.
 * Below min → 0, above max → 0.
 */
static float bell_score(float val, float min, float peak, float max)
{
    if (val <= min || val >= max)
        return 0.0f;
    if (val < peak)
        return (val - min) / (peak - min);
    else
        return (max - val) / (max - peak);
}

/**
 * Redox sub-score: linear ramp from REDOX_RAMP_LOW to REDOX_GOOD_MIN,
 * then 1.0 in the good range, then penalty above REDOX_GOOD_MAX.
 */
static float redox_score(float orp_mv)
{
    if (orp_mv < REDOX_RAMP_LOW)
        return 0.0f;
    if (orp_mv < REDOX_GOOD_MIN)
        return (orp_mv - REDOX_RAMP_LOW) / (REDOX_GOOD_MIN - REDOX_RAMP_LOW);
    if (orp_mv <= REDOX_GOOD_MAX)
        return 1.0f;
    /* Above good range: penalty (too dry / oxidized / sterile) */
    float over = orp_mv - REDOX_GOOD_MAX;
    return fmaxf(0.0f, 1.0f - over / 200.0f);  /* -1 per 200 mV over */
}

void shi_compute(terra_reading_t *r)
{
    /* Temperature-corrected respiration (Q10 to 20 °C reference) */
    float temp_ratio = (Q10_REF_TEMP - r->temp_c) / 10.0f;
    float q10_corr = powf(Q10_FACTOR, temp_ratio);
    float resp_corrected = r->flux_mgC * q10_corr;

    /* Sub-scores */
    r->shi_resp = bell_score(resp_corrected,
                             RESP_OPT_MIN, RESP_OPT_PEAK, RESP_OPT_MAX);
    r->shi_redox = redox_score((float)r->orp_mv);
    r->shi_ec = bell_score((float)r->ec_us,
                           EC_OPT_MIN, EC_OPT_PEAK, EC_OPT_MAX);
    r->shi_moist = bell_score(r->moisture_vwc,
                              MOIST_OPT_MIN, MOIST_OPT_PEAK, MOIST_OPT_MAX);
    r->shi_temp = bell_score(r->temp_c,
                             TEMP_OPT_MIN, TEMP_OPT_PEAK, TEMP_OPT_MAX);

    /* Weighted sum → 0–100 */
    float shi_f = SHI_WEIGHT_RESP   * r->shi_resp
                + SHI_WEIGHT_REDOX  * r->shi_redox
                + SHI_WEIGHT_EC     * r->shi_ec
                + SHI_WEIGHT_MOIST  * r->shi_moist
                + SHI_WEIGHT_TEMP   * r->shi_temp;

    shi_f *= 100.0f;
    if (shi_f > 100.0f) shi_f = 100.0f;
    if (shi_f < 0.0f)   shi_f = 0.0f;

    r->shi = (uint8_t)(shi_f + 0.5f);

    ESP_LOGI(TAG, "SHI=%d  resp=%.2f redox=%.2f ec=%.2f moist=%.2f temp=%.2f"
             "  (flux=%.1f mgC, orp=%d mV, ec=%u µS, vwc=%.1f%%, T=%.1f°C)",
             r->shi, r->shi_resp, r->shi_redox, r->shi_ec,
             r->shi_moist, r->shi_temp,
             r->flux_mgC, r->orp_mv, r->ec_us,
             r->moisture_vwc, r->temp_c);
}