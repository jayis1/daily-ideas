/*
 * ble_bridge.h — UART protocol to ESP32-C3 (BLE GATT server)
 */

#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

void ble_bridge_init(void);
bool ble_bridge_poll_cmd(char *cmd, size_t len);
void ble_bridge_push_results(float sos, float bua, float si, float t, float z, int cls);
void ble_bridge_push_waveform(const uint16_t *buf, uint32_t n);
void ble_bridge_push_status(float bat_v, int state, float sos, float bua);

#endif