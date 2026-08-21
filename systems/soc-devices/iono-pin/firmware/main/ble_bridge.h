/*
 * ble_bridge.h — UART protocol to ESP32-C3 BLE/Wi-Fi bridge
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include "ims.h"
#include "library.h"
#include <stdbool.h>

void ble_bridge_init(void);
void ble_bridge_send_spectrum(const ims_result_t *r, const classify_result_t *cls);
void ble_bridge_send_status(const char *status);

#endif /* BLE_BRIDGE_H */