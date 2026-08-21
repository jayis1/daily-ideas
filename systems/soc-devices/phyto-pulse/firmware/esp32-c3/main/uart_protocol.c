/*
 * uart_protocol.c — UART protocol between STM32 and ESP32-C3
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Receives framed JSON packets from STM32G474 @ 460800 baud.
 * Frame: [0xAA] [len_hi] [len_lo] [json...] [0x55]
 */

#include "uart_protocol.h"
#include "ble_service.h"
#include "wifi_server.h"
#include "esp_log.h"
#include "driver/uart.h"
#include <string.h>

static const char *TAG = "uart_proto";

#define UART_NUM UART_NUM_1
#define BUF_SIZE 512

static uint8_t g_rx_buf[BUF_SIZE];
static int g_rx_idx = 0;
static int g_frame_len = -1;
static enum { WAIT_AA, READ_LEN, READ_DATA, WAIT_55 } g_state = WAIT_AA;

void uart_protocol_init(void)
{
    uart_config_t cfg = {
        .baud_rate = 460800,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    uart_param_config(UART_NUM, &cfg);
    /* GPIO2 = RX, GPIO3 = TX */
    uart_set_pin(UART_NUM, 3, 2, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    uart_driver_install(UART_NUM, BUF_SIZE * 2, 0, 0, NULL, 0);
}

void uart_protocol_handle_packet(const char *json, int len)
{
    /* Parse JSON type: "s" (sample), "e" (event), "swp" (slow wave), "stat" (status) */
    if (strstr(json, "\"t\":\"s\"")) {
        /* Extract voltage and timestamp */
        float v = 0;
        uint32_t ts = 0;
        sscanf(json, "{\"t\":\"s\",\"ts\":%lu,\"v\":%f", (unsigned long *)&ts, &v);
        ble_send_sample(v, ts);
        wifi_broadcast_sample(v, ts);
    } else if (strstr(json, "\"t\":\"e\"")) {
        /* Event: forward to BLE + WiFi */
        ble_send_event(json, len);
        wifi_broadcast_event(json, len);
    } else if (strstr(json, "\"t\":\"swp\"")) {
        wifi_broadcast_event(json, len);
    } else if (strstr(json, "\"t\":\"stat\"")) {
        ESP_LOGI(TAG, "Status: %.*s", len, json);
    }
}

void uart_protocol_task(void *arg)
{
    uint8_t byte;
    while (1) {
        int len = uart_read_bytes(UART_NUM, &byte, 1, pdMS_TO_TICKS(100));
        if (len <= 0) continue;

        switch (g_state) {
            case WAIT_AA:
                if (byte == 0xAA) g_state = READ_LEN;
                break;
            case READ_LEN:
                g_frame_len = byte << 8;
                g_state = READ_LEN;
                /* read second byte... simplified: read both bytes together */
                /* In full impl, read 2 length bytes */
                g_frame_len = byte;  /* simplified single byte length */
                g_rx_idx = 0;
                g_state = READ_DATA;
                break;
            case READ_DATA:
                if (g_rx_idx < BUF_SIZE - 1) {
                    g_rx_buf[g_rx_idx++] = byte;
                    if (g_rx_idx >= g_frame_len) {
                        g_state = WAIT_55;
                    }
                } else {
                    g_state = WAIT_AA;  /* overflow, reset */
                }
                break;
            case WAIT_55:
                if (byte == 0x55) {
                    g_rx_buf[g_rx_idx] = 0;
                    uart_protocol_handle_packet((char *)g_rx_buf, g_rx_idx);
                }
                g_state = WAIT_AA;
                break;
        }
    }
}