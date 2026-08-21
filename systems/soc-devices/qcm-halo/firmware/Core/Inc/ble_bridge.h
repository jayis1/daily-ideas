/*
 * ble_bridge.h — UART protocol to ESP32-C3 for BLE + Wi-Fi
 */

#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include "config.h"

/* Initialize UART to ESP32-C3 */
void ble_bridge_init(void);

/* Check if BLE client is connected (queried from ESP32-C3) */
uint8_t ble_service_is_connected(void);

/* Send result data to ESP32-C3 (forwarded via BLE GATT notify) */
void ble_send_result(const qcm_result_t *r);
void ble_send_sweep(const overtone_sweep_t *s);
void ble_send_voigt(const voigt_params_t *v);
void ble_send_status(float temp, float vbat, const char *state);
void ble_send_raw(const char *data, uint16_t len);

/* Receive commands from phone app (via ESP32-C3) */
typedef enum {
    BLE_CMD_NONE,
    BLE_CMD_START_MEASURE,
    BLE_CMD_STOP,
    BLE_CMD_SET_CHANNEL,
    BLE_CMD_SET_OVERTONE,
    BLE_CMD_SET_TEMP,
    BLE_CMD_SET_PUMP,
    BLE_CMD_SET_VALVE,
    BLE_CMD_CALIBRATE,
    BLE_CMD_START_EXPERIMENT,
    BLE_CMD_GET_STATUS,
    BLE_CMD_SET_PARAMS
} ble_cmd_t;

ble_cmd_t ble_get_command(acq_params_t *params);
void ble_poll_commands(acq_params_t *params);

#endif /* BLE_BRIDGE_H */