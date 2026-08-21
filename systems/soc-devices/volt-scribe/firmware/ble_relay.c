/*
 * volt-scribe — ble_relay.c
 * UART relay to ESP32-C3 for BLE streaming
 *
 * Protocol: simple binary frames over UART at 115200 baud
 * Frame format:
 *   [0xAA] [0x55] [type] [len] [data...] [crc8]
 *
 * Types:
 *   0x01 = Data point (4 bytes float E, 4 bytes float I)
 *   0x02 = EIS point (4 bytes Z_real, 4 bytes Z_imag, 4 bytes freq)
 *   0x03 = Status (1 byte: mode + state)
 *   0x04 = Peak report (4 bytes E, 4 bytes I, 1 byte type)
 *   0x05 = Randles fit (4×4 bytes: R_s, R_ct, C_dl, alpha)
 */

#include "ble_relay.h"
#include <string.h>

extern UART_HandleTypeDef huart1;

#define FRAME_HEADER_1  0xAA
#define FRAME_HEADER_2  0x55

/* ── Init ──────────────────────────────────────────────────────── */

void ble_relay_init(void)
{
    /* UART1 already initialized by main */
    /* Send startup beacon to ESP32-C3 */
    uint8_t beacon[] = {0xAA, 0x55, 0x03, 0x01, 0x01, 0x00};
    HAL_UART_Transmit(&huart1, beacon, sizeof(beacon), 50);
}

/* ── CRC8 ───────────────────────────────────────────────────────── */

static uint8_t crc8(const uint8_t *data, int len)
{
    uint8_t crc = 0;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80)
                crc = (crc << 1) ^ 0x07;
            else
                crc <<= 1;
        }
    }
    return crc;
}

/* ── Send data point ───────────────────────────────────────────── */

void ble_relay_send_point(float x, float y)
{
    uint8_t frame[13];
    frame[0] = FRAME_HEADER_1;
    frame[1] = FRAME_HEADER_2;
    frame[2] = 0x01;  /* Data point type */
    frame[3] = 8;     /* Length */
    memcpy(&frame[4], &x, 4);
    memcpy(&frame[8], &y, 4);
    frame[12] = crc8(&frame[4], 8);
    HAL_UART_Transmit(&huart1, frame, sizeof(frame), 50);
}

/* ── Send EIS point ────────────────────────────────────────────── */

void ble_relay_send_eis_point(float z_real, float z_imag, float freq)
{
    uint8_t frame[17];
    frame[0] = FRAME_HEADER_1;
    frame[1] = FRAME_HEADER_2;
    frame[2] = 0x02;  /* EIS point type */
    frame[3] = 12;    /* Length */
    memcpy(&frame[4], &z_real, 4);
    memcpy(&frame[8], &z_imag, 4);
    memcpy(&frame[12], &freq, 4);
    frame[16] = crc8(&frame[4], 12);
    HAL_UART_Transmit(&huart1, frame, sizeof(frame), 50);
}

/* ── Poll for incoming commands from ESP32-C3 ──────────────────── */

void ble_relay_poll(void)
{
    /* Check for incoming BLE commands from ESP32-C3 */
    uint8_t rx_byte;
    if (HAL_UART_Receive(&huart1, &rx_byte, 1, 0) == HAL_OK) {
        /* Process command from BLE client */
        /* Commands: start, stop, change mode, etc. */
        /* For now: echo back as debug */
    }
}