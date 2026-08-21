/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/ble_ndt.h — BLE GATT server for NDT data
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef BLE_NDT_H
#define BLE_NDT_H

#include <stdbool.h>
#include <stdint.h>

void ble_ndt_init(void);
bool ble_ndt_is_connected(void);

/* Push a measurement notification to connected clients. */
void ble_ndt_notify_measurement(const uint8_t *data, uint8_t len);

/* Push an A-scan chunk. */
void ble_ndt_notify_ascan(const uint8_t *data, uint8_t len);

/* Push status. */
void ble_ndt_notify_status(uint8_t armed, uint8_t measuring, uint8_t bat);

/* Register a callback for commands received from the phone app (write to
 * the command characteristic). The callback should forward to the STM32. */
typedef void (*ble_cmd_cb_t)(uint8_t cmd, const uint8_t *payload, uint8_t len);
void ble_ndt_register_cmd(ble_cmd_cb_t cb);

#endif /* BLE_NDT_H */