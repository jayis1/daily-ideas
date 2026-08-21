/*
 * ble_bridge.h — UART protocol to ESP32-C3 BLE GATT server
 */
#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include <stdint.h>
#include <stdbool.h>
#include "demod.h"
#include "sweep.h"

void ble_bridge_init(void);

/* Push a demod result (R/θ/X/Y/noise) at 100 Hz */
void ble_bridge_push_demod(const demod_result_t *r, float freq, float gain);

/* Push a sweep point */
void ble_bridge_push_sweep(const sweep_point_t *p);

/* Push a status string */
void ble_bridge_push_status(const char *msg);

/* Check for incoming commands from the BLE host (via ESP32-C3) */
bool ble_bridge_poll_cmd(char *cmd, size_t len);

#endif /* BLE_BRIDGE_H */