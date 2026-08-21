/*
 * ble_bridge.h — UART bridge to ESP32-C3 for BLE/Wi-Fi
 */

#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include <stdint.h>
#include "eem.h"
#include "library.h"

/**
 * Initialize UART bridge to ESP32-C3.
 */
void ble_bridge_init(void);

/**
 * Send EEM data to ESP32-C3 for BLE/Wi-Fi streaming.
 * @param eem  EEM data
 * @return 0 on success, -1 on error
 */
int ble_bridge_send_eem(const eem_t *eem);

/**
 * Send classification result.
 */
int ble_bridge_send_result(const classify_result_t *result);

/**
 * Send device status (battery, state, temperature).
 * @param state    Current device state
 * @param battery  Battery percentage
 * @param temp_c   Temperature in °C
 */
int ble_bridge_send_status(uint8_t state, uint8_t battery, float temp_c);

/**
 * Send log entry (CSV line).
 */
int ble_bridge_send_log(const char *csv_line);

/**
 * Send calibration data.
 */
int ble_bridge_send_calibration(const uint8_t *data, uint16_t len);

/**
 * Poll for incoming commands from ESP32-C3.
 * @param cmd     Output command byte
 * @param payload Output payload buffer
 * @param len     Output payload length
 * @return 1 if command received, 0 if none, -1 on error
 */
int ble_bridge_poll(uint8_t *cmd, uint8_t *payload, uint16_t *len);

/**
 * Check if BLE/Wi-Fi is connected.
 * @return 1 if connected, 0 if not
 */
int ble_bridge_connected(void);

/**
 * CRC16-CCITT calculation.
 */
uint16_t ble_bridge_crc16(const uint8_t *data, uint16_t len);

#endif /* BLE_BRIDGE_H */