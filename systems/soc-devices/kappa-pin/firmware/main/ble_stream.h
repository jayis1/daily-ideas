/*
 * kappa-pin / firmware / main / ble_stream.h
 * BLE GATT interface for live data streaming + commands
 *
 * MIT License.
 */
#ifndef BLE_STREAM_H
#define BLE_STREAM_H

#include <stdbool.h>
#include "measurement.h"

/* BLE UUIDs */
#define UUID_KAPPA_SERVICE    0x9101
#define UUID_KAPPA_DATA       0x9102
#define UUID_KAPPA_RESULT     0x9103
#define UUID_KAPPA_CMD        0x9104
#define UUID_KAPPA_INFO       0x9105

/* Command codes (write to UUID_KAPPA_CMD) */
#define BLE_CMD_START         0x01
#define BLE_CMD_STOP          0x02
#define BLE_CMD_SET_MATERIAL  0x03  /* payload: 1 byte material ID */
#define BLE_CMD_SET_POWER     0x04  /* payload: 4 bytes float power W */
#define BLE_CMD_CALIBRATE     0x05
#define BLE_CMD_GET_INFO      0x06

/* Initialize BLE peripheral */
void ble_stream_init(void);

/* Send a temperature sample (8 bytes: ts_u16 + dT_x4_s16 + Q_x4_s16) */
void ble_stream_send_sample(const meas_sample_t *s);

/* Send measurement result */
void ble_stream_send_result(const meas_result_t *r);

/* Check if a client is connected */
bool ble_stream_is_connected(void);

/* Set callback for incoming commands */
typedef void (*ble_cmd_callback_t)(uint8_t cmd, const uint8_t *payload, int len);
void ble_stream_set_cmd_callback(ble_cmd_callback_t cb);

#endif /* BLE_STREAM_H */