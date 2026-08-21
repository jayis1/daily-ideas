/*
 * ble_custom.h — Custom BLE GATT service API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef BLE_CUSTOM_H
#define BLE_CUSTOM_H

#include "esp_err.h"
#include <stdint.h>

/**
 * @brief Initialize custom BLE GATT service.
 */
esp_err_t ble_custom_init(void);

/**
 * @brief Update the last recognized character and confidence.
 */
esp_err_t ble_custom_update_char(int char_id, float confidence);

/**
 * @brief Set active user profile (0-3).
 */
esp_err_t ble_custom_set_profile(uint8_t profile);

/**
 * @brief Get active user profile.
 */
uint8_t ble_custom_get_profile(void);

/**
 * @brief Set recognition mode (0=auto, 1=letters, 2=numbers).
 */
esp_err_t ble_custom_set_mode(uint8_t mode);

/**
 * @brief Set battery level for BLE reporting.
 */
esp_err_t ble_custom_set_battery(uint8_t level);

#endif /* BLE_CUSTOM_H */