/*
 * ble_bridge.c — UART bridge to ESP32-C3 for BLE/WiFi streaming
 *
 * STM32G491 communicates with ESP32-C3-MINI-1 via USART2 (PA2 TX, PA3 RX)
 * at 921600 baud. Simple framing protocol:
 *
 * Frame: [SYNC1][SYNC2][MSG_TYPE][LEN][payload...][CRC8]
 *   SYNC1 = 0xAA, SYNC2 = 0x55
 *   MSG_TYPE = one of BLE_MSG_*
 *   LEN = payload length (0-255)
 *   CRC8 = CRC-8 over MSG_TYPE + LEN + payload
 */

#include "stm32g491_conf.h"
#include "ble_bridge.h"
#include <string.h>

#define SYNC1 0xAA
#define SYNC2 0x55

static uint8_t crc8(const uint8_t *data, uint8_t len) {
    uint8_t crc = 0x00;
    for (uint8_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int b = 0; b < 8; b++) {
            if (crc & 0x80) crc = (crc << 1) ^ 0x07;
            else           crc <<= 1;
        }
    }
    return crc;
}

static void uart2_send_byte(uint8_t byte) {
    USART2_TDR = byte;
    while (!(USART2_ISR & (1U << 7))) ;  /* TC: transmission complete */
}

static void ble_send_frame(uint8_t msg_type, const uint8_t *payload, uint8_t len) {
    uart2_send_byte(SYNC1);
    uart2_send_byte(SYNC2);
    uart2_send_byte(msg_type);
    uart2_send_byte(len);

    /* CRC over type + len + payload */
    uint8_t crc_buf[260];
    crc_buf[0] = msg_type;
    crc_buf[1] = len;
    if (payload && len > 0) memcpy(crc_buf + 2, payload, len);
    uint8_t crc = crc8(crc_buf, len + 2);

    for (uint8_t i = 0; i < len; i++) {
        uart2_send_byte(payload[i]);
    }
    uart2_send_byte(crc);
}

void ble_init(void) {
    /* Enable USART2 clock */
    RCC_APB1ENR1 |= (1U << 17);  /* USART2EN */

    /* PA2 TX, PA3 RX as AF7 (USART2) */
    GPIO_MODER(GPIOA_BASE) &= ~((3U << (2*2)) | (3U << (3*2)));
    GPIO_MODER(GPIOA_BASE) |=  (2U << (2*2)) | (2U << (3*2));
    GPIO_AFRL(GPIOA_BASE) = (GPIO_AFRL(GPIOA_BASE) & ~((0xF << (2*4)) | (0xF << (3*4))))
                           | (7U << (2*4)) | (7U << (3*4));

    /* PB15: ESP32-C3 EN pin, output, default HIGH (enabled) */
    GPIO_MODER(GPIOB_BASE) |= (1U << (15*2));
    GPIO_SET(ESP_EN_PORT, ESP_EN_PIN);

    /* USART2: 921600 baud, 8N1 */
    USART2_CR1 = 0;
    USART2_BRR = SYS_CLK_HZ / 921600U;
    USART2_CR1 = (1U << 3)   /* TE: transmitter enable */
               | (1U << 2)    /* RE: receiver enable */
               | (1U << 0);   /* UE: USART enable */
}

void ble_enable(void) {
    GPIO_SET(ESP_EN_PORT, ESP_EN_PIN);
}

void ble_disable(void) {
    GPIO_CLR(ESP_EN_PORT, ESP_EN_PIN);
}

void ble_send_data(float temp, float heat_flow, float time, float setpoint) {
    /* 16 bytes: 4 floats × 4 bytes each */
    uint8_t payload[16];
    memcpy(payload + 0,  &temp,      4);
    memcpy(payload + 4,  &heat_flow, 4);
    memcpy(payload + 8,  &time,      4);
    memcpy(payload + 12, &setpoint,  4);
    ble_send_frame(BLE_MSG_DATA, payload, 16);
}

void ble_send_status(float temp, float setpoint, float heat_flow,
                      float ramp_rate, uint8_t battery, uint8_t state) {
    /* 14 bytes: 4 floats + 1 byte + 1 byte (padded) */
    uint8_t payload[16];
    memcpy(payload + 0,  &temp,      4);
    memcpy(payload + 4,  &setpoint,  4);
    memcpy(payload + 8,  &heat_flow, 4);
    memcpy(payload + 12, &ramp_rate, 4);
    /* Truncate to 14: drop last 2 bytes of ramp_rate, add battery + state */
    payload[14] = battery;
    payload[15] = state;
    ble_send_frame(BLE_MSG_STATUS, payload, 16);
}

void ble_send_match(const char *name, float confidence) {
    uint8_t payload[28];
    uint8_t name_len = (uint8_t)strlen(name);
    if (name_len > 23) name_len = 23;
    payload[0] = name_len;
    memcpy(payload + 1, name, name_len);
    memcpy(payload + 24, &confidence, 4);
    ble_send_frame(BLE_MSG_MATCH, payload, 28);
}

void ble_send_done(void) {
    ble_send_frame(BLE_MSG_DONE, NULL, 0);
}

void ble_send_calib(float t_measured, float t_expected, float correction) {
    uint8_t payload[12];
    memcpy(payload + 0, &t_measured, 4);
    memcpy(payload + 4, &t_expected, 4);
    memcpy(payload + 8, &correction, 4);
    ble_send_frame(BLE_MSG_CALIB, payload, 12);
}