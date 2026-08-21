/**
 * spiro_flow/ble_bridge.h — BLE/WiFi bridge via ESP32-C3
 */
#ifndef SPIRO_FLOW_BLE_BRIDGE_H
#define SPIRO_FLOW_BLE_BRIDGE_H

#include "main.h"

int ble_bridge_init(void);
void ble_bridge_send_result(const spiro_result_t *r);
void ble_bridge_send_flow_data(const maneuver_buffer_t *m);
void ble_bridge_poll(void);

#endif