/*
 * cor-sono / firmware / ble_stream.h
 */
#pragma once
#include "main.h"

void ble_stream_init(void);
void ble_send_audio_block(const int16_t *stereo, int n);
void ble_send_result(int class_id, int confidence, int hr);
bool ble_is_connected(void);

/* BLE advertising data (defined here for simplicity) */
static const esp_ble_adv_data_t adv_data = {
    .set_scan_rsp = false,
    .include_name = true,
    .include_txpower = true,
    .min_interval = 0x20,
    .max_interval = 0x40,
    .appearance = 0x00,
    .manufacturer_len = 0,
    .p_manufacturer_data = NULL,
    .service_data_len = 0,
    .p_service_data = NULL,
    .service_uuid_len = 0,
    .p_service_uuid = NULL,
    .flag = (ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT),
};