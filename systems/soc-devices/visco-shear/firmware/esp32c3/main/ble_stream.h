/*
 * visco-shear / firmware / esp32c3 / main / ble_stream.h
 */
#ifndef BLE_STREAM_H
#define BLE_STREAM_H

#include <stdint.h>
#include <stddef.h>

void ble_stream_init(void);
void ble_stream_process_frame(const uint8_t *data, int len);

#endif