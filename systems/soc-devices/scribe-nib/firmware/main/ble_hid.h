/*
 * ble_hid.h — BLE HID Keyboard service API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef BLE_HID_H
#define BLE_HID_H

#include "esp_err.h"
#include <stdbool.h>

/**
 * @brief Initialize BLE HID keyboard service.
 * @param device_name  BLE advertising name
 */
esp_err_t ble_hid_init(const char *device_name);

/**
 * @brief Send a character as a HID keystroke.
 * @param c  ASCII character to send
 */
esp_err_t ble_hid_send_key(char c);

/**
 * @brief Check if BLE is currently connected.
 */
bool ble_hid_is_connected(void);

#endif /* BLE_HID_H */