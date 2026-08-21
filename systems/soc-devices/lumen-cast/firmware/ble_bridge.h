/**
 * lumen_cast/firmware/ble_bridge.h — UART protocol to ESP32-C3
 */
#ifndef LUMEN_CAST_BLE_BRIDGE_H
#define LUMEN_CAST_BLE_BRIDGE_H

int ble_bridge_init(void);
void ble_bridge_send_result(const photo_result_t *r);
void ble_bridge_send_scan_data(const scan_buffer_t *s);
void ble_bridge_send_ies_file(const scan_buffer_t *s);
void ble_bridge_poll(void);

#endif