/*
 * Pulse Hound — RF Signal Hunter
 * ble_stream.h — BLE streaming interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_BLE_STREAM_H
#define PULSE_HOUND_BLE_STREAM_H

#include "config.h"

typedef void (*ble_notification_cb_t)(const char *char_uuid, const uint8_t *data, uint8_t len);
typedef void (*ble_mode_write_cb_t)(uint8_t mode);

int  ble_stream_init(ble_notification_cb_t callback, ble_mode_write_cb_t mode_cb);
void ble_stream_rssi(float rssi_dbm);
void ble_stream_spectrum_row(const uint8_t *row_data, int len);
void ble_stream_bearing(float bearing_deg, float peak_rssi);
void ble_stream_classification(signal_class_t cls);
void ble_stream_battery(int pct);
int  ble_stream_is_connected(void);
void ble_stream_set_logging(int enabled);
int  ble_stream_is_logging(void);

#endif /* PULSE_HOUND_BLE_STREAM_H */