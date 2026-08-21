/*
 * kappa-pin / firmware / main / probe.c
 * Probe interface — detection, temperature, equilibrium checking
 *
 * MIT License.
 */
#include "probe.h"
#include "adc24.h"
#include "esp_log.h"
#include "driver/adc.h"
#include <math.h>

static const char *TAG = "probe";

static probe_info_t current_probe;
static bool probe_detected = false;
static float temp_history[60];   /* last 60 temperature readings */
static int temp_history_idx = 0;
static int temp_history_count = 0;
static int64_t temp_history_time[60];

/* Probe info database */
static const probe_info_t probe_db[] = {
    [PROBE_NONE] = {
        .type = PROBE_NONE, .heater_resistance = 0, .active_length = 0,
        .rtd_r0 = 1000, .name = "None", .standard = "",
    },
    [PROBE_NEEDLE] = {
        .type = PROBE_NEEDLE, .heater_resistance = 1.0f, .active_length = 0.080f,
        .rtd_r0 = 1000, .name = "NP-100", .standard = "ASTM D5334",
    },
    [PROBE_HOTWIRE] = {
        .type = PROBE_HOTWIRE, .heater_resistance = 30.0f, .active_length = 0.060f,
        .rtd_r0 = 1000, .name = "HW-60", .standard = "ASTM D7896",
    },
    [PROBE_SURFACE] = {
        .type = PROBE_SURFACE, .heater_resistance = 15.0f, .active_length = 0.040f,
        .rtd_r0 = 1000, .name = "SP-40", .standard = "Surface line-source",
    },
};

probe_type_t probe_detect(void)
{
    /* Read probe ID via ADC2 (GPIO37)
     * Voltage divider: V_id = 3.3V * R_id / (R_id + 10kΩ)
     *   0Ω   (needle)   → ~0V     → ADC ≈ 0
     *   10kΩ (hot-wire) → 1.65V   → ADC ≈ 2048
     *   22kΩ (surface)  → 2.28V   → ADC ≈ 2830
     *   open (none)     → 3.3V    → ADC ≈ 4095
     */
    int raw = 0;
    /* ADC2 on ESP32-S3 — must be acquired and released */
    for (int i = 0; i < 8; i++) {
        int val;
        if (adc_oneshot_read(adc2_handle, ADC2_CHANNEL_0, &val) == ESP_OK) {
            raw = (raw + val) / 2 + val / 2;  /* simple averaging */
        }
        vTaskDelay(pdMS_TO_TICKS(1));
    }

    probe_type_t type;
    if (raw < 500) {
        type = PROBE_NEEDLE;
    } else if (raw > 1700 && raw < 2400) {
        type = PROBE_HOTWIRE;
    } else if (raw > 2500 && raw < 3200) {
        type = PROBE_SURFACE;
    } else if (raw > 3800) {
        type = PROBE_NONE;
    } else {
        type = PROBE_NEEDLE;  /* default fallback */
    }

    ESP_LOGI(TAG, "Probe ID ADC=%d → type=%d (%s)", raw, type, probe_type_name(type));

    current_probe = probe_db[type];
    probe_detected = (type != PROBE_NONE);

    return type;
}

const probe_info_t *probe_get_info(void)
{
    if (!probe_detected) probe_detect();
    return &current_probe;
}

float probe_read_temperature(void)
{
    float temp;
    if (adc24_read_temperature(&temp) == ADC_OK) {
        return temp;
    }
    return -999.0f;
}

void probe_update(void)
{
    float temp = probe_read_temperature();
    if (temp < -100.0f) return;  /* read error */

    temp_history[temp_history_idx] = temp;
    temp_history_time[temp_history_idx] = esp_timer_get_time();
    temp_history_idx = (temp_history_idx + 1) % 60;
    if (temp_history_count < 60) temp_history_count++;
}

bool probe_is_equilibrium(float drift_threshold_c_per_s, float duration_s)
{
    if (temp_history_count < (int)(duration_s * 10.0f)) return false;  /* need enough samples */

    /* Compute drift rate over last 'duration_s' seconds */
    int n_needed = (int)(duration_s * 10.0f);  /* assuming 10 Hz update */
    if (n_needed > temp_history_count) n_needed = temp_history_count;

    int idx_new = temp_history_idx - 1;
    if (idx_new < 0) idx_new = 59;
    int idx_old = (idx_new - n_needed + 60) % 60;

    float t_new = temp_history[idx_new];
    float t_old = temp_history[idx_old];
    int64_t dt_us = temp_history_time[idx_new] - temp_history_time[idx_old];
    float dt_s = dt_us / 1e6f;

    if (dt_s < 0.1f) return false;

    float drift = fabsf(t_new - t_old) / dt_s;  /* °C/s */
    return (drift < drift_threshold_c_per_s);
}

const char *probe_type_name(probe_type_t t)
{
    switch (t) {
        case PROBE_NONE:     return "None";
        case PROBE_NEEDLE:   return "Needle (NP-100)";
        case PROBE_HOTWIRE:  return "Hot-wire (HW-60)";
        case PROBE_SURFACE:  return "Surface (SP-40)";
        default:             return "Unknown";
    }
}