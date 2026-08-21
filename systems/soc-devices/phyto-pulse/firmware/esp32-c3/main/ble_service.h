/*
 * ble_service.h — BLE GATT server for Phyto Pulse
 */

#ifndef BLE_SERVICE_H
#define BLE_SERVICE_H

#include <stdint.h>

/* GATT characteristics */
#define CHAR_WAVEFORM_UUID   0xFF01  /* Live waveform samples (notify) */
#define CHAR_EVENT_UUID      0xFF02  /* Spike events (notify) */
#define CHAR_STATUS_UUID     0xFF03  /* Device status (read+notify) */
#define CHAR_COMMAND_UUID    0xFF04  /* Commands (write) */

void ble_service_init(void);
void ble_notify_task(void *arg);
void ble_service_send_status(void);

/* Send a waveform sample to connected clients */
void ble_send_sample(float voltage_mv, uint32_t timestamp_ms);

/* Send an event notification */
void ble_send_event(const char *json, int len);

/* Send a command response */
void ble_send_command_response(const char *response);

#endif /* BLE_SERVICE_H */