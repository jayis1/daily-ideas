/**
 * terra_pin/moisture.c — Capacitive soil moisture probe (MCB-01-A)
 *
 * The MCB-01-A capacitive probe outputs a 555-timer oscillator frequency
 * that varies with soil dielectric constant. Dry soil → high frequency
 * (~850 Hz), wet soil → low frequency (~350 Hz). VWC is computed by
 * linear interpolation between calibrated dry/wet endpoints.
 *
 * The frequency is measured using ESP32 PCNT (pulse counter) over a
 * 1-second gate window.
 */

#include "moisture.h"
#include "esp_log.h"
#include "driver/pcnt.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "MOIST";

static float g_freq_dry = MOIST_FREQ_DRY_DEFAULT;
static float g_freq_wet = MOIST_FREQ_WET_DEFAULT;

esp_err_t moisture_init(void)
{
    ESP_LOGI(TAG, "Initializing capacitive moisture probe (PCNT on GPIO%d)",
             PIN_MOIST_FREQ);

    /* Load calibration from NVS */
    nvs_handle_t h;
    if (nvs_open("terra_pin", NVS_READONLY, &h) == ESP_OK) {
        int32_t dry = 0, wet = 0;
        if (nvs_get_i32(h, "moist_dry", &dry) == ESP_OK)
            g_freq_dry = (float)dry;
        if (nvs_get_i32(h, "moist_wet", &wet) == ESP_OK)
            g_freq_wet = (float)wet;
        nvs_close(h);
        ESP_LOGI(TAG, "Calibration loaded: dry=%.0f Hz, wet=%.0f Hz",
                 g_freq_dry, g_freq_wet);
    }

    /* Configure PCNT */
    pcnt_config_t pcnt_cfg = {
        .pulse_gpio_num = PIN_MOIST_FREQ,
        .ctrl_gpio_num  = PCNT_PIN_NOT_USED,
        .channel        = PCNT_CHANNEL_0,
        .unit           = PCNT_UNIT_0,
        .pos_mode       = PCNT_COUNT_INC,
        .neg_mode       = PCNT_COUNT_DIS,
        .lctrl_mode     = PCNT_MODE_KEEP,
        .hctrl_mode     = PCNT_MODE_KEEP,
        .counter_h_lim  = 10000,
        .counter_l_lim  = 0,
    };
    esp_err_t ret = pcnt_unit_config(&pcnt_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "PCNT config failed: %s", esp_err_to_name(ret));
        return ret;
    }

    pcnt_set_filter_value(PCNT_UNIT_0, 100);
    pcnt_filter_enable(PCNT_UNIT_0);
    pcnt_counter_clear(PCNT_UNIT_0);
    pcnt_counter_resume(PCNT_UNIT_0);

    ESP_LOGI(TAG, "Moisture probe initialized");
    return ESP_OK;
}

esp_err_t moisture_read(float *vwc)
{
    /* Clear counter, wait 1 second, read count = frequency in Hz */
    pcnt_counter_clear(PCNT_UNIT_0);
    vTaskDelay(pdMS_TO_TICKS(1000));
    int16_t count = 0;
    pcnt_get_counter_value(PCNT_UNIT_0, &count);

    float freq = (float)count;

    /* Linear interpolation: dry (high freq) = 0%, wet (low freq) = 100% */
    if (freq >= g_freq_dry) {
        *vwc = 0.0f;
    } else if (freq <= g_freq_wet) {
        *vwc = 100.0f;
    } else {
        *vwc = (g_freq_dry - freq) / (g_freq_dry - g_freq_wet) * 100.0f;
    }

    ESP_LOGI(TAG, "Freq: %.0f Hz → VWC: %.1f %%", freq, *vwc);
    return ESP_OK;
}

esp_err_t moisture_calibrate(float freq_dry, float freq_wet)
{
    g_freq_dry = freq_dry;
    g_freq_wet = freq_wet;

    nvs_handle_t h;
    if (nvs_open("terra_pin", NVS_READWRITE, &h) == ESP_OK) {
        nvs_set_i32(h, "moist_dry", (int32_t)freq_dry);
        nvs_set_i32(h, "moist_wet", (int32_t)freq_wet);
        nvs_commit(h);
        nvs_close(h);
        ESP_LOGI(TAG, "Calibration saved: dry=%.0f, wet=%.0f", freq_dry, freq_wet);
        return ESP_OK;
    }
    return ESP_ERR_NVS_NOT_INITIALIZED;
}