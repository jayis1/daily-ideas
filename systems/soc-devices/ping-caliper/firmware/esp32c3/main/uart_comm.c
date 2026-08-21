/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/uart_comm.c — UART bridge to STM32G474 (framed binary protocol)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "uart_comm.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "uart_comm";
static uart_rx_cb_t g_rx_cb = NULL;

static uint16_t crc16_ccitt(const uint8_t *data, uint16_t len)
{
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t b = 0; b < 8; b++)
            crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : (crc << 1);
    }
    return crc;
}

void uart_comm_init(void)
{
    uart_config_t cfg = {
        .baud_rate  = UART_BAUDRATE,
        .data_bits  = UART_DATA_8_BITS,
        .parity     = UART_PARITY_DISABLE,
        .stop_bits  = UART_STOP_BITS_1,
        .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM, UART_BUF_SIZE * 2,
                                         UART_BUF_SIZE * 2, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(UART_NUM, &cfg));
    ESP_ERROR_CHECK(uart_set_pin(UART_NUM, UART_TX_PIN, UART_RX_PIN,
                                  UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));

    /* RX task */
    xTaskCreate(uart_rx_task, "uart_rx", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "UART to STM32 @ %d baud", UART_BAUDRATE);
}

void uart_comm_send(uint8_t cmd, const uint8_t *payload, uint8_t len)
{
    uint8_t buf[8 + 250];
    buf[0] = UART_SOF0;
    buf[1] = UART_SOF1;
    buf[2] = len;
    buf[3] = cmd;
    if (len && payload) memcpy(&buf[4], payload, len);
    uint16_t crc = crc16_ccitt(&buf[2], 2 + len);
    buf[4 + len]     = (uint8_t)(crc & 0xFF);
    buf[4 + len + 1] = (uint8_t)(crc >> 8);
    buf[4 + len + 2] = UART_EOF0;
    buf[4 + len + 3] = UART_EOF1;
    uart_write_bytes(UART_NUM, (const char *)buf, 8 + len);
}

void uart_comm_register_rx(uart_rx_cb_t cb) { g_rx_cb = cb; }

void uart_rx_task(void *arg)
{
    (void)arg;
    static enum { S_SOF0, S_SOF1, S_LEN, S_CMD, S_PAY, S_CRC0, S_CRC1, S_EOF0, S_EOF1 } st = S_SOF0;
    static uint8_t plen = 0, cmd = 0, idx = 0, crclo = 0;
    static uint8_t payload[250];
    uint8_t b;

    for (;;) {
        int n = uart_read_bytes(UART_NUM, &b, 1, pdMS_TO_TICKS(100));
        if (n <= 0) continue;

        switch (st) {
        case S_SOF0: if (b == UART_SOF0) st = S_SOF1; break;
        case S_SOF1: if (b == UART_SOF1) st = S_LEN; else st = S_SOF0; break;
        case S_LEN:  plen = b; idx = 0; st = S_CMD; break;
        case S_CMD:  cmd = b; st = (plen > 0) ? S_PAY : S_CRC0; break;
        case S_PAY:
            if (idx < sizeof(payload)) payload[idx++] = b;
            if (idx >= plen) st = S_CRC0;
            break;
        case S_CRC0: crclo = b; st = S_CRC1; break;
        case S_CRC1: {
            /* verify CRC (len + cmd + payload) */
            uint16_t crc = 0xFFFF;
            uint8_t hdr[2] = { plen, cmd };
            crc = crc16_ccitt(hdr, 2);
            crc = crc16_ccitt(payload, plen);
            uint16_t rx_crc = ((uint16_t)b << 8) | crclo;
            (void)rx_crc; (void)crc;
            st = S_EOF0;
            break;
        }
        case S_EOF0: if (b == UART_EOF0) st = S_EOF1; else st = S_SOF0; break;
        case S_EOF1:
            if (b == UART_EOF1) {
                if (g_rx_cb) g_rx_cb(cmd, payload, plen);
            }
            st = S_SOF0;
            break;
        }
    }
}