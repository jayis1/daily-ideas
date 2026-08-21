/*
 * ble_bridge.h — UART bridge to ESP32-C3 for BLE/WiFi streaming (header)
 */
#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include <stdint.h>
#include <stdbool.h>

#define BLE_MSG_DATA     0x01
#define BLE_MSG_STATUS   0x02
#define BLE_MSG_MATCH    0x03
#define BLE_MSG_DONE     0x04
#define BLE_MSG_CALIB    0x05

void    ble_init(void);
void    ble_send_data(float temp, float heat_flow, float time, float setpoint);
void    ble_send_status(float temp, float setpoint, float heat_flow,
                          float ramp_rate, uint8_t battery, uint8_t state);
void    ble_send_match(const char *name, float confidence);
void    ble_send_done(void);
void    ble_send_calib(float t_measured, float t_expected, float correction);
void    ble_enable(void);
void    ble_disable(void);

#endif /* BLE_BRIDGE_H */