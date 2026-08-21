/*
 * Therma Weave — Safety Watchdog
 * safety_watchdog.c — Over-temperature and over-current protection
 *
 * SPDX-License-Identifier: MIT
 */

#include "safety_watchdog.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "SAFETY";

/* Auto-retry cooldown: 30 seconds after shutdown */
#define AUTO_RETRY_COOLDOWN_US  (30 * 1000000LL)
/* Maximum auto-retry attempts before requiring manual reset */
#define MAX_AUTO_RETRIES        3

/* Over-temperature threshold for hardware watchdog check */
#define HW_OVERTEMP_THRESHOLD   70.0f  /* °C — hardware comparator threshold */

void safety_watchdog_init(safety_watchdog_t *sw, uint8_t safety_shutdown_pin)
{
    sw->safety_shutdown_pin = safety_shutdown_pin;
    sw->fault_bitmap = FAULT_NONE;
    sw->global_shutdown = false;
    sw->shutdown_time = 0;
    sw->fault_count = 0;
    sw->auto_retry_count = 0;
    sw->auto_retry_time = 0;

    for (int i = 0; i < 4; i++) {
        sw->fault_history[i] = FAULT_NONE;
    }

    /* Initialize safety shutdown pin as output, initially LOW (heaters enabled) */
    gpio_set_level(safety_shutdown_pin, 0);

    ESP_LOGI(TAG, "Safety watchdog initialized (shutdown pin=%d)", safety_shutdown_pin);
}

void safety_watchdog_fault(safety_watchdog_t *sw, fault_type_t fault, uint8_t zone)
{
    if (zone >= 4) zone = 0;

    sw->fault_bitmap |= fault;
    sw->fault_history[zone] |= fault;
    sw->fault_count++;

    ESP_LOGE(TAG, "SAFETY FAULT: type=0x%02X, zone=%d, total=%d",
             fault, zone, sw->fault_count);

    /* Over-temperature and over-current trigger immediate shutdown */
    if (fault & (FAULT_OVERTEMP | FAULT_OVERCURRENT)) {
        safety_watchdog_emergency_shutdown(sw);
    }
}

void safety_watchdog_clear_faults(safety_watchdog_t *sw)
{
    sw->fault_bitmap = FAULT_NONE;
    for (int i = 0; i < 4; i++) {
        sw->fault_history[i] = FAULT_NONE;
    }
    sw->auto_retry_count = 0;
    ESP_LOGI(TAG, "All faults cleared");
}

void safety_watchdog_emergency_shutdown(safety_watchdog_t *sw)
{
    sw->global_shutdown = true;
    sw->shutdown_time = esp_timer_get_time();

    /* Drive hardware shutdown pin HIGH to force all MOSFETs off */
    gpio_set_level(sw->safety_shutdown_pin, 1);

    ESP_LOGE(TAG, "=== EMERGENCY SHUTDOWN ACTIVATED ===");
    ESP_LOGE(TAG, "All heaters disabled. Hardware shutdown pin driven HIGH.");

    /* Set auto-retry timer */
    sw->auto_retry_count++;
    sw->auto_retry_time = sw->shutdown_time + AUTO_RETRY_COOLDOWN_US;
}

bool safety_watchdog_try_recover(safety_watchdog_t *sw)
{
    if (!sw->global_shutdown) return true;

    /* Check if cooldown period has elapsed */
    int64_t now = esp_timer_get_time();
    if (now < sw->auto_retry_time) {
        ESP_LOGI(TAG, "Cooldown period not elapsed. %lld s remaining.",
                 (sw->auto_retry_time - now) / 1000000LL);
        return false;
    }

    /* Check if we've exceeded max retries */
    if (sw->auto_retry_count > MAX_AUTO_RETRIES) {
        ESP_LOGE(TAG, "Max auto-retries exceeded (%d). Manual reset required.",
                 MAX_AUTO_RETRIES);
        return false;
    }

    /* Clear shutdown */
    sw->global_shutdown = false;
    gpio_set_level(sw->safety_shutdown_pin, 0);  /* Re-enable heaters */
    safety_watchdog_clear_faults(sw);

    ESP_LOGI(TAG, "Safety watchdog recovered. Heaters re-enabled (attempt %d/%d).",
             sw->auto_retry_count, MAX_AUTO_RETRIES);
    return true;
}

bool safety_watchdog_is_shutdown(safety_watchdog_t *sw)
{
    return sw->global_shutdown;
}

bool safety_watchdog_has_fault(safety_watchdog_t *sw)
{
    return sw->fault_bitmap != FAULT_NONE;
}

void safety_watchdog_task(void *pvParameters)
{
    safety_watchdog_t *sw = (safety_watchdog_t *)pvParameters;

    ESP_LOGI(TAG, "Safety watchdog task started (10 Hz check rate)");

    while (1) {
        /* If in shutdown, try to recover after cooldown */
        if (sw->global_shutdown) {
            safety_watchdog_try_recover(sw);
        }

        /* Check if overcurrent alert pin is active (active low) */
        /* Real: if (!gpio_get_level(CURRENT_ALERT_PIN)) { safety_watchdog_fault(...); } */

        vTaskDelay(pdMS_TO_TICKS(100));  /* 10 Hz */
    }
}