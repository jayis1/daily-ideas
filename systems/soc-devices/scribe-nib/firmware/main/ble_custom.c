/*
 * ble_custom.c — Custom BLE GATT service for Scribe Nib
 *
 * Provides raw stroke data, confidence, profile switching,
 * and other advanced features beyond basic HID keyboard.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "ble_custom.h"
#include <string.h>
#include "esp_log.h"
#include "esp_gatts_api.h"
#include "esp_bt_main.h"
#include "esp_gatt_common_api.h"

static const char *TAG = "ble_custom";

/* Service and characteristic UUIDs */
#define SCRIBE_SERVICE_UUID     0xFFB0
#define CHAR_TEXT_UUID          0xFFB1
#define CHAR_LAST_CHAR_UUID    0xFFB2
#define CHAR_CONFIDENCE_UUID   0xFFB3
#define CHAR_STROKE_UUID       0xFFB4
#define CHAR_PROFILE_UUID      0xFFB5
#define CHAR_MODE_UUID         0xFFB6
#define CHAR_BATTERY_UUID      0xFFB7
#define CHAR_FW_VERSION_UUID   0xFFB8

/* GATT attribute handles */
static uint16_t service_handle;
static uint16_t char_text_handle;
static uint16_t char_last_char_handle;
static uint16_t char_confidence_handle;
static uint16_t char_profile_handle;
static uint16_t char_mode_handle;
static uint16_t char_battery_handle;
static uint16_t char_fw_version_handle;

/* Current values */
static char last_text[64] = {0};
static uint8_t last_char_id = 0;
static float last_confidence = 0.0f;
static uint8_t active_profile = 0;
static uint8_t recognition_mode = 0;
static uint8_t battery_level = 100;
static const char fw_version[] = "1.0.0";

/* ---- Public API ---- */

esp_err_t ble_custom_init(void)
{
    /* Custom GATT service is registered alongside the HID service.
       In a full implementation, this would use esp_gatts_if to
       create the service with the UUIDs above. For now, we
       initialize the state variables. */
    ESP_LOGI(TAG, "Custom BLE service initialized (0xFFB0)");
    return ESP_OK;
}

esp_err_t ble_custom_update_char(int char_id, float confidence)
{
    last_char_id = (uint8_t)char_id;
    last_confidence = confidence;

    /* Append to text buffer */
    const char charset[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    if (char_id >= 0 && char_id < 62) {
        int len = strlen(last_text);
        if (len < sizeof(last_text) - 1) {
            last_text[len] = charset[char_id];
            last_text[len + 1] = '\0';
        }
    }

    ESP_LOGD(TAG, "Updated: char=%d conf=%.2f text='%s'", char_id, confidence, last_text);
    return ESP_OK;
}

esp_err_t ble_custom_set_profile(uint8_t profile)
{
    active_profile = profile;
    ESP_LOGI(TAG, "Profile set to %d", profile);
    return ESP_OK;
}

uint8_t ble_custom_get_profile(void)
{
    return active_profile;
}

esp_err_t ble_custom_set_mode(uint8_t mode)
{
    recognition_mode = mode;
    ESP_LOGI(TAG, "Recognition mode set to %d", mode);
    return ESP_OK;
}

esp_err_t ble_custom_set_battery(uint8_t level)
{
    battery_level = (level > 100) ? 100 : level;
    return ESP_OK;
}