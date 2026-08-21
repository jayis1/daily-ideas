/*
 * ble_bridge.h — UART protocol to ESP32-C3 BLE bridge
 */

#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include "quant.h"

/* Initialize UART1 to ESP32-C3 (921600 baud) */
void ble_bridge_init(void);

/* Send electropherogram chunk (for live streaming) */
void ble_bridge_send_eph_chunk(const float *eph, uint32_t count,
                               float hv_kv, float current_ua);

/* Send final results (peak table) */
void ble_bridge_send_results(const ion_result_t *results, uint8_t count,
                             uint16_t run_id);

/* Send error */
void ble_bridge_send_error(const char *msg, float current_ua, float voltage_kv);

#endif /* BLE_BRIDGE_H */