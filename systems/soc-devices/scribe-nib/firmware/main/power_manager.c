/*
 * power_manager.c — Power state management for Scribe Nib
 *
 * Implements 4-state power management:
 *   ACTIVE  → IDLE → LIGHT_SLEEP → DEEP_SLEEP
 * With automatic transitions based on inactivity timers.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "power_manager.h"
#include <string.h>
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_pm.h"
#include "driver/rtc_io.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "power";

/* Inactivity timeout thresholds (seconds) */
#define IDLE_TIMEOUT_SEC       5      /* No writing for 5s → IDLE */
#define LIGHT_SLEEP_TIMEOUT   30     /* 30s idle → LIGHT_SLEEP */
#define DEEP_SLEEP_TIMEOUT    300    /* 5min no activity → DEEP_SLEEP */

/* Current power state */
static power_state_t current_state = POWER_STATE_ACTIVE;
static int64_t last_activity_time = 0;  /* microseconds since boot */
static esp_pm_config_esp32s3_t pm_config;

void power_manager_init(void)
{
    /* Configure ESP32-S3 power management */
    pm_config.max_freq_mhz = 240;
    pm_config.min_freq_mhz = 40;    /* Drop to 40MHz in light sleep */
    pm_config.light_sleep_enable = true;

    esp_err_t err = esp_pm_configure(&pm_config);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "PM configure failed: 0x%X", err);
    }

    last_activity_time = esp_timer_get_time();
    current_state = POWER_STATE_ACTIVE;

    ESP_LOGI(TAG, "Power manager initialized (max=%dMHz, min=%dMHz)",
             pm_config.max_freq_mhz, pm_config.min_freq_mhz);
}

void power_manager_update(void)
{
    int64_t now = esp_timer_get_time();
    int64_t idle_us = now - last_activity_time;

    power_state_t new_state = current_state;

    switch (current_state) {
        case POWER_STATE_ACTIVE:
            if (idle_us > (int64_t)IDLE_TIMEOUT_SEC * 1000000) {
                new_state = POWER_STATE_IDLE;
            }
            break;

        case POWER_STATE_IDLE:
            if (idle_us > (int64_t)LIGHT_SLEEP_TIMEOUT * 1000000) {
                new_state = POWER_STATE_LIGHT_SLEEP;
            }
            break;

        case POWER_STATE_LIGHT_SLEEP:
            if (idle_us > (int64_t)DEEP_SLEEP_TIMEOUT * 1000000) {
                new_state = POWER_STATE_DEEP_SLEEP;
            }
            break;

        case POWER_STATE_DEEP_SLEEP:
            /* Cannot reach here — deep sleep resets MCU */
            break;
    }

    if (new_state != current_state) {
        power_manager_transition(new_state);
    }
}

void power_manager_transition(power_state_t new_state)
{
    ESP_LOGI(TAG, "Power state: %d → %d", current_state, new_state);

    switch (new_state) {
        case POWER_STATE_ACTIVE:
            /* Resume full speed, enable OLED, enable BLE advertising */
            /* ESP PM will automatically scale frequency up */
            break;

        case POWER_STATE_IDLE:
            /* Reduce IMU ODR to 20Hz, keep BLE connected, OLED off */
            break;

        case POWER_STATE_LIGHT_SLEEP:
            /* IMU at 1Hz (motion detect only), BLE advertising only */
            break;

        case POWER_STATE_DEEP_SLEEP:
            /* Configure wake sources and enter deep sleep */
            esp_sleep_enable_timer_wakeup(2 * 1000000);  /* 2s for BLE adv */
            esp_sleep_enable_touchpad_wakeup();
            ESP_LOGI(TAG, "Entering deep sleep...");
            esp_deep_sleep_start();
            /* Does not return — MCU resets on wake */
            break;
    }

    current_state = new_state;
}

void power_manager_wake(void)
{
    last_activity_time = esp_timer_get_time();

    if (current_state != POWER_STATE_ACTIVE) {
        power_manager_transition(POWER_STATE_ACTIVE);
    }
}

void power_manager_activity(void)
{
    last_activity_time = esp_timer_get_time();
}

power_state_t power_manager_get_state(void)
{
    return current_state;
}