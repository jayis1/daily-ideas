/*
 * ble_bridge.c — UART protocol to ESP32-C3 BLE/Wi-Fi bridge
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * Binary frame protocol over UART2 @ 921600 baud:
 *   [0xAA][0x55][type][len_hi][len_lo][payload...][crc16_lo][crc16_hi]
 * type 0x01 = spectrum + verdict, 0x02 = status text, 0x03 = fault
 *
 * ESP32-C3 re-broadcasts over BLE (live spectrum + verdict) and serves
 * a Wi-Fi web UI for CSV download / OTA.
 *
 * SPDX-License-Identifier: MIT
 */
#include "ble_bridge.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"
#include <string.h>

extern UART_HandleTypeDef huart2;

static uint16_t crc16(const uint8_t *d, int n)
{
    uint16_t c = 0;
    for (int i = 0; i < n; i++) {
        c ^= d[i];
        for (int j = 0; j < 8; j++)
            c = (c & 1) ? (c >> 1) ^ 0xA001 : (c >> 1);
    }
    return c;
}

static void send_frame(uint8_t type, const uint8_t *payload, uint16_t len)
{
    uint8_t hdr[5] = { 0xAA, 0x55, type, (uint8_t)(len >> 8), (uint8_t)(len & 0xFF) };
    HAL_UART_Transmit(&huart2, hdr, 5, 20);
    if (len && payload) HAL_UART_Transmit(&huart2, (uint8_t *)payload, len, 50);
    uint16_t crc = crc16(payload, len);
    uint8_t crcb[2] = { (uint8_t)(crc & 0xFF), (uint8_t)(crc >> 8) };
    HAL_UART_Transmit(&huart2, crcb, 2, 20);
}

void ble_bridge_init(void)
{
    /* UART2 already initialized in main clock setup */
}

void ble_bridge_send_spectrum(const ims_result_t *r, const classify_result_t *cls)
{
    /* payload: [pressure f32][drift_T f32][amb_T f32][n_peaks u8]
     *          [K0 f32 * n_peaks][amp i16 * n_peaks]
     *          [name_len u8][name bytes][class u8][conf f32] */
    uint8_t buf[200];
    int n = 0;
    memcpy(buf + n, &r->pressure_kpa, 4); n += 4;
    memcpy(buf + n, &r->drift_temp_c, 4); n += 4;
    memcpy(buf + n, &r->ambient_temp_c, 4); n += 4;
    buf[n++] = r->num_peaks;
    for (int i = 0; i < r->num_peaks; i++) {
        memcpy(buf + n, &r->peaks[i].k0, 4); n += 4;
    }
    for (int i = 0; i < r->num_peaks; i++) {
        memcpy(buf + n, &r->peaks[i].amplitude, 2); n += 2;
    }
    uint8_t namelen = (uint8_t)strlen(cls->name);
    buf[n++] = namelen;
    memcpy(buf + n, cls->name, namelen); n += namelen;
    buf[n++] = (uint8_t)cls->cls;
    memcpy(buf + n, &cls->confidence, 4); n += 4;
    /* also append the 140-sample averaged spectrum for live plotting */
    for (int i = 0; i < IMS_SAMPLES_PER_SWEEP; i++) {
        buf[n++] = (uint8_t)((r->spectrum[i] >> 8) & 0xFF);  /* high byte */
    }
    send_frame(0x01, buf, (uint16_t)n);
}

void ble_bridge_send_status(const char *status)
{
    send_frame(0x02, (const uint8_t *)status, (uint16_t)strlen(status));
}