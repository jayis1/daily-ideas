/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * ble_config.h — BLE GATT service for phone-based configuration
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef BLE_CONFIG_H
#define BLE_CONFIG_H

#include "config.h"

/* Initialize BLE advertising and the Mussel Watch GATT service */
int ble_config_init(mussel_watch_state_t *st);

/* Start BLE advertising (config mode) */
void ble_config_start_advertising(void);

/* Stop BLE advertising */
void ble_config_stop_advertising(void);

/* Process BLE events (call in main loop if not using SoftDevice callback) */
void ble_config_poll(mussel_watch_state_t *st);

/* Check if a BLE command is pending (e.g., calibrate_closed) */
int ble_config_get_command(mussel_watch_state_t *st);

/* Update notify characteristics with live data (gape angles, WQ) */
void ble_config_update_notify(const mussel_watch_state_t *st);

#endif /* BLE_CONFIG_H */