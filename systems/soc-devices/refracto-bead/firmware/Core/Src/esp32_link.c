/**
 * esp32_link.c — UART protocol to ESP32-C3
 *
 * Sends measurement results from the STM32 to the ESP32-C3 over USART1
 * at 460800 baud. The ESP32-C3 parses the frames and relays via BLE/Wi-Fi.
 *
 * Frame format:
 *   [0xAA][0x55][cmd][len_hi][len_lo][payload...][crc8]
 */

#include "esp32_link.h"
#include <string.h>

extern UART_HandleTypeDef huart1;

#define FRAME_SYNC1  0xAA
#define FRAME_SYNC2  0x55

#define CMD_RESULT   0x01
#define CMD_STATUS   0x02
#define CMD_CAL      0x03

/* CRC-8 (poly 0x07, init 0x00) */
static uint8_t crc8(const uint8_t *data, int len) {
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

static void send_frame(uint8_t cmd, const uint8_t *payload, uint16_t len) {
    uint8_t header[5];
    header[0] = FRAME_SYNC1;
    header[1] = FRAME_SYNC2;
    header[2] = cmd;
    header[3] = (len >> 8) & 0xFF;
    header[4] = len & 0xFF;

    HAL_UART_Transmit(&huart1, header, 5, 100);
    if (len > 0 && payload) {
        HAL_UART_Transmit(&huart1, (uint8_t *)payload, len, 200);
    }
    uint8_t crc = crc8(payload, len);
    HAL_UART_Transmit(&huart1, &crc, 1, 50);
}

void esp32_link_init(UART_HandleTypeDef *huart) {
    (void)huart;  /* Uses huart1 extern */
}

void esp32_link_send_result(const ri_result_t *result) {
    if (!result) return;

    /* Serialize the result into a compact binary payload */
    uint8_t payload[80];
    int idx = 0;

    /* RI values (4 × float32 = 16 bytes) */
    memcpy(&payload[idx], result->n, 16); idx += 16;

    /* n_D, n_F, n_C, dispersion, abbe_vd (5 × float32 = 20 bytes) */
    memcpy(&payload[idx], &result->n_D, 4); idx += 4;
    memcpy(&payload[idx], &result->n_F, 4); idx += 4;
    memcpy(&payload[idx], &result->n_C, 4); idx += 4;
    memcpy(&payload[idx], &result->dispersion, 4); idx += 4;
    memcpy(&payload[idx], &result->abbe_vd, 4); idx += 4;

    /* Derived: brix, sg, abv, freeze_point (4 × float32 = 16 bytes) */
    memcpy(&payload[idx], &result->brix, 4); idx += 4;
    memcpy(&payload[idx], &result->specific_grav, 4); idx += 4;
    memcpy(&payload[idx], &result->abv, 4); idx += 4;
    memcpy(&payload[idx], &result->freeze_point, 4); idx += 4;

    /* Temperatures (2 × float32 = 8 bytes) */
    memcpy(&payload[idx], &result->t_prism, 4); idx += 4;
    memcpy(&payload[idx], &result->t_ambient, 4); idx += 4;

    /* Compound ID (1 byte) + confidence (float32 = 4 bytes) */
    payload[idx++] = (uint8_t)result->compound_id;
    memcpy(&payload[idx], &result->confidence, 4); idx += 4;

    /* Compound name (16 bytes, null-padded) */
    memcpy(&payload[idx], result->compound_name, 16); idx += 16;

    send_frame(CMD_RESULT, payload, idx);
}

void esp32_link_send_status(uint8_t status, uint8_t battery) {
    uint8_t payload[2] = { status, battery };
    send_frame(CMD_STATUS, payload, 2);
}