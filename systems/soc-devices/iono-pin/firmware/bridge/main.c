/*
 * main.c — ESP32-C3-MINI-1 BLE/Wi-Fi bridge for Iono Pin
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * Receives UART binary frames from the STM32G474 (type 0x01 spectrum+verdict,
 * 0x02 status), re-broadcasts:
 *   - BLE GATT notify: live spectrum + compound + confidence
 *   - Wi-Fi HTTP server: JSON status + CSV download + OTA
 *
 * UART: GPIO4 (RX from STM32 TX), GPIO5 (TX to STM32 RX) @ 921600.
 *
 * SPDX-License-Identifier: MIT
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "nvs_flash.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_wifi.h"
#include "esp_http_server.h"

#define UART_NUM       UART_NUM_1
#define UART_RX_PIN    4
#define UART_TX_PIN    5
#define UART_BAUD       921600
#define FRAME_MAX        256

static uint8_t rxbuf[FRAME_MAX];
static volatile int frame_ready = 0;
static uint16_t frame_len = 0;

/* ---- minimal frame parser ---- */
static void uart_rx_task(void *arg)
{
    uint8_t b;
    enum { S_AA, S_55, S_TYPE, S_LEN_HI, S_LEN_LO, S_PAYLOAD, S_CRC_LO, S_CRC_HI } s = S_AA;
    uint8_t type = 0; uint16_t len = 0; uint16_t idx = 0; uint16_t crc = 0;
    while (1) {
        int n = uart_read_bytes(UART_NUM, &b, 1, portMAX_DELAY);
        if (n <= 0) continue;
        switch (s) {
        case S_AA:     if (b == 0xAA) s = S_55; break;
        case S_55:     if (b == 0x55) s = S_TYPE; else s = S_AA; break;
        case S_TYPE:   type = b; s = S_LEN_HI; break;
        case S_LEN_HI: len = b << 8; s = S_LEN_LO; break;
        case S_LEN_LO: len |= b; idx = 0; crc = 0;
                       if (len == 0) s = S_CRC_LO; else s = S_PAYLOAD; break;
        case S_PAYLOAD: rxbuf[idx++] = b; crc ^= b;
                        for (int j=0;j<8;j++) crc = (crc&1)?(crc>>1)^0xA001:(crc>>1);
                        if (idx >= len) s = S_CRC_LO; break;
        case S_CRC_LO: if ((crc & 0xFF) == b) s = S_CRC_HI; else s = S_AA; break;
        case S_CRC_HI: if ((crc >> 8) == b) { frame_ready = 1; frame_len = len; }
                       s = S_AA; break;
        }
    }
}

/* ---- BLE GATT (abbreviated) ---- */
#define GATT_SERVICE_UUID 0x18A0
#define GATT_CHAR_UUID    0x2BE0

static esp_ble_gatts_cb_t g_gatts_app;

static void gatts_event_handler(esp_gatts_cb_event_t ev, esp_gatt_if_t g, union ble_gatts_evt *p)
{
    /* minimal: advertise + notify on frame_ready */
}

static void ble_init(void)
{
    esp_bt_controller_mem_release(ESP_BT_MODE_BLE);
    esp_bt_controller_config_t cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();
    /* register service + char (omitted for brevity) */
}

/* ---- Wi-Fi + HTTP server (abbreviated) ---- */
static httpd_handle_t g_server;
static esp_err_t status_handler(httpd_req_t *req)
{
    char body[128];
    int n = snprintf(body, sizeof(body),
        "{\"name\":\"iono-pin\",\"status\":\"OK\",\"vbat\":%.2f}\r\n", 3.9f);
    httpd_resp_send(req, body, n);
    return ESP_OK;
}
static httpd_uri_t status_uri = { .uri="/status", .method=HTTP_GET, .handler=status_handler };

static void wifi_init_sta(void)
{
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    wifi_config_t wc = { .sta = { .ssid = "iono-pin", .password = "configureme" } };
    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wc);
    esp_wifi_start();
    /* In AP mode, serve a small status+CSV page */
}

static void http_server_start(void)
{
    httpd_config_t c = HTTPD_DEFAULT_CONFIG();
    httpd_start(&g_server, &c);
    httpd_register_uri_handler(g_server, &status_uri);
}

void app_main(void)
{
    nvs_flash_init();
    /* UART init */
    uart_config_t uc = { .baud_rate = UART_BAUD, .data_bits = UART_DATA_8_BITS,
                         .parity = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
                         .flow_ctrl = UART_HW_FLOWCTRL_DISABLE, .source_clk = UART_SCLK_APB };
    uart_driver_install(UART_NUM, 2048, 2048, 0, NULL, 0);
    uart_param_config(UART_NUM, &uc);
    uart_set_pin(UART_NUM, UART_TX_PIN, UART_RX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    ble_init();
    wifi_init_sta();
    http_server_start();

    xTaskCreate(uart_rx_task, "uart_rx", 4096, NULL, 5, NULL);

    while (1) {
        if (frame_ready) {
            frame_ready = 0;
            /* forward via BLE notify + http; abbreviated */
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}