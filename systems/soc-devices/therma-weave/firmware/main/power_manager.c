/*
 * Therma Weave — Power Manager
 * power_manager.c — Battery monitoring and power management
 *
 * SPDX-License-Identifier: MIT
 */

#include "power_manager.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "driver/adc.h"

static const char *TAG = "POWER";

void power_manager_init(power_manager_t *pm)
{
    pm->vbat = VBAT_NOMINAL;
    pm->vbus = 0.0f;
    pm->charging = false;
    pm->low_battery = false;
    pm->battery_pct = 100;

    ESP_LOGI(TAG, "Power manager initialized");
}

float power_manager_read_battery(power_manager_t *pm)
{
    /* Read ADC2 channel 1 (GPIO21) for battery voltage */
    int raw = 0;
    /* Real: adc2_get_raw(ADC2_CHANNEL_1, ADC_WIDTH_BIT_12, &raw); */
    raw = 2048;  /* Placeholder: midpoint ≈ 11.1V */

    /* Convert ADC value to voltage */
    /* ADC raw (0-4095) → voltage at ADC pin → battery voltage */
    /* VBAT = ADC_raw × 3.3V / 4095 × (110kΩ / 10kΩ) */
    /* VBAT = ADC_raw × 0.008862 */
    pm->vbat = (float)raw * VBAT_DIVIDER_RATIO;

    /* Update battery percentage */
    pm->battery_pct = power_manager_battery_pct(pm->vbat);

    /* Check low battery */
    if (pm->vbat < VBAT_LOW && pm->vbat > 1.0f) {
        pm->low_battery = true;
        ESP_LOGW(TAG, "Low battery: %.2f V (%d%%)", pm->vbat, pm->battery_pct);
    } else {
        pm->low_battery = false;
    }

    /* Check critical battery */
    if (pm->vbat < VBAT_CRITICAL && pm->vbat > 1.0f) {
        ESP_LOGE(TAG, "CRITICAL battery: %.2f V! Entering deep sleep.", pm->vbat);
        power_manager_deep_sleep(0);  /* Sleep indefinitely */
    }

    return pm->vbat;
}

uint8_t power_manager_battery_pct(float vbat)
{
    /* Simple linear interpolation from 10.5V (0%) to 12.6V (100%) */
    if (vbat >= VBAT_FULL) return 100;
    if (vbat <= VBAT_LOW) return 0;

    float pct = (vbat - VBAT_LOW) / (VBAT_FULL - VBAT_LOW) * 100.0f;
    if (pct > 100.0f) pct = 100.0f;
    if (pct < 0.0f) pct = 0.0f;

    return (uint8_t)pct;
}

void power_manager_deep_sleep(uint32_t duration_ms)
{
    ESP_LOGI(TAG, "Entering deep sleep for %lu ms", (unsigned long)duration_ms);

    /* Ensure all heaters are OFF before sleeping */
    /* Real: set all PWM outputs to 0, set safety shutdown HIGH */

    if (duration_ms > 0) {
        esp_sleep_enable_timer_wakeup((uint64_t)duration_ms * 1000);  /* Convert ms to µs */
    }

    esp_deep_sleep_start();
}