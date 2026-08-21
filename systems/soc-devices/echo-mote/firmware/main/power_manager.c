/**
 * power_manager.c — Battery monitoring, deep sleep, charge status
 *
 * Battery voltage is sensed via a 1:2 resistive divider on GPIO39 (ADC1_CH3).
 * Charge status comes from MCP73831 STAT pin on GPIO38.
 */

#include "power_manager.h"
#include "esp_log.h"
#include "driver/adc.h"
#include "nvs_flash.h"
#include "nvs.h"

static const char *TAG = "power";

#define VBAT_SENSE_ADC   ADC1_CHANNEL_3  /* GPIO39 */
#define CHARGE_STAT_GPIO 38
#define NVS_NAMESPACE    "echo_mote"
#define NVS_SPL_KEY      "spl_offset"

static float spl_offset = 0.0f;

int power_manager_init(void) {
    ESP_LOGI(TAG, "Initializing power manager");

    /* Configure ADC for battery voltage sensing */
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(VBAT_SENSE_ADC, ADC_ATTEN_DB_11);  /* 0-3.6V range */

    /* Configure charge status GPIO */
    gpio_config_t io_cfg = {
        .pin_bit_mask = (1ULL << CHARGE_STAT_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&io_cfg);

    /* Load SPL calibration from NVS */
    nvs_handle_t nvs;
    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs) == ESP_OK) {
        if (nvs_get_f32(nvs, NVS_SPL_KEY, &spl_offset) != ESP_OK) {
            spl_offset = 0.0f;
        }
        nvs_close(nvs);
    }

    ESP_LOGI(TAG, "Power manager ready (SPL offset: %.1f dB)", spl_offset);
    return 0;
}

float power_manager_read_battery(void) {
    /* Read ADC and convert to voltage
     * Divider: VBAT → 100kΩ → ADC → 100kΩ → GND
     * ADC reads half the battery voltage.
     * With ADC_ATTEN_DB_11, full-scale ≈ 3.6V at ADC input
     * So battery V = ADC_reading / 4096 × 3.6 × 2
     */
    int raw = adc1_get_raw(VBAT_SENSE_ADC);
    if (raw < 0) raw = 0;
    float adc_v = (float)raw / 4096.0f * 3.6f;
    float vbat = adc_v * 2.0f;  /* Account for 1:2 divider */
    return vbat;
}

void power_manager_cal_spl(float db_offset) {
    spl_offset = db_offset;

    /* Store in NVS */
    nvs_handle_t nvs;
    if (nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs) == ESP_OK) {
        nvs_set_f32(nvs, NVS_SPL_KEY, spl_offset);
        nvs_commit(nvs);
        nvs_close(nvs);
    }
    ESP_LOGI(TAG, "SPL calibration offset: %.1f dB", spl_offset);
}

float power_manager_get_spl_offset(void) {
    return spl_offset;
}