/*
 * ble_bridge.h — UART protocol to ESP32-C3 BLE GATT server
 *
 * STM32 ↔ ESP32-C3 via UART (USART1, PA9/PA10, 921600 baud).
 * ESP32-C3 exposes BLE GATT characteristics:
 *   - PM2.5 (µg/m³)
 *   - PM10 (µg/m³)
 *   - 16-bin histogram (uint32 array)
 *   - Flow (L/min)
 *   - T, RH, P
 *   - Command (START/STOP/CALIB/ZERO)
 */

#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include <stdint.h>
#include <stdbool.h>

void   ble_bridge_init(void);
bool   ble_bridge_poll_cmd(char *cmd, uint32_t maxlen);
void   ble_bridge_push_status(float battery_v, int state, float flow,
                                float pm1, float pm25, float pm10,
                                const uint32_t *counts, uint8_t n);

#endif /* BLE_BRIDGE_H */