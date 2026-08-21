/*
 * ble.h — FerroWeave BLE GATT service
 */
#ifndef FERRO_WEAVE_BLE_H
#define FERRO_WEAVE_BLE_H

#include <stdint.h>
#include <stddef.h>

/* BLE service / characteristic UUIDs (custom, 128-bit). */
#define FW_SERVICE_UUID "8a7b3c2d-1e0f-4a1b-9c3d-2e1f0a1b2c3d"
#define FW_CMD_UUID     "8a7b3c2d-1e0f-4a1b-9c3d-2e1f0a1b2c3e"
#define FW_SWEEP_UUID   "8a7b3c2d-1e0f-4a1b-9c3d-2e1f0a1b2c3f"

void ble_init(void);

/* Push a sweep frame (already decoded payload) to connected clients. */
void ble_notify_sweep(const uint8_t *payload, uint16_t len);

/* Push a status string to connected clients. */
void ble_notify_status(const char *s);

/* Register a callback for commands written by the client. */
typedef void (*ble_cmd_cb_t)(const char *cmd, int len);
void ble_set_cmd_callback(ble_cmd_cb_t cb);

#endif /* FERRO_WEAVE_BLE_H */