/* ble.h — BLE GATT server for Taste Bead
 *
 * Exposes measurement results, impedance spectra, and library management
 * over BLE 5.0 GATT characteristics.
 */

#ifndef TASTE_BEAD_BLE_H
#define TASTE_BEAD_BLE_H

#include "esp_err.h"
#include "eis.h"
#include <stdint.h>

/* Forward declarations (defined in main.c) */
typedef struct {
    char label[32];
    float confidence;
    float distance;
    int lib_index;
    int64_t timestamp_us;
} ble_result_t;

/* Initialize BLE GATT server */
esp_err_t ble_init(void);

/* Send classification result via BLE notification */
esp_err_t ble_send_result(const ble_result_t *result);

/* Send full impedance spectrum via BLE notification (chunked) */
esp_err_t ble_send_spectrum(const eis_result_t *eis);

/* Send status message */
esp_err_t ble_send_status(const char *status_msg);

/* Check if a BLE client is connected */
bool ble_is_connected(void);

/* Get last command received from BLE client */
esp_err_t ble_get_command(uint8_t *cmd, uint8_t *data, int *len);

/* Command opcodes (received from phone) */
#define BLE_CMD_IDENTIFY       0x01
#define BLE_CMD_LEARN          0x02
#define BLE_CMD_DELETE         0x03
#define BLE_CMD_LIST_LIBRARY  0x04
#define BLE_CMD_CALIBRATE      0x05
#define BLE_CMD_MONITOR_START  0x06
#define BLE_CMD_MONITOR_STOP   0x07
#define BLE_CMD_SET_MODE       0x08
#define BLE_CMD_GET_STATUS     0x09

#endif /* TASTE_BEAD_BLE_H */