/*
 * ble_bridge.h — ESP32-C3 UART bridge for BLE/Wi-Fi
 */

#ifndef BLE_BRIDGE_H
#define BLE_BRIDGE_H

#include <stdint.h>
#include "interferometer.h"
#include "dsp.h"
#include "main.h"

void ble_bridge_init(void);
void ble_bridge_send_result(const measure_result_t *r);
void ble_bridge_send_fft(const fft_result_t *fft);
void ble_bridge_send_stream(const phase_block_t *pb, uint32_t t_ms);
void ble_bridge_handle_commands(acq_params_t *params);

#endif /* BLE_BRIDGE_H */