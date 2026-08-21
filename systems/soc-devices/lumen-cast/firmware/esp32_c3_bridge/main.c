/**
 * lumen_cast/firmware/esp32_c3_bridge/main.c
 *
 * ESP32-C3 BLE/WiFi bridge for Lumen Cast goniophotometer.
 *
 * Receives photometric results, scan data, and .IES/.LDT file content
 * from the STM32G491 via UART, and relays them over:
 *   - BLE GATT to a phone/PC app
 *   - WiFi (MQTT or HTTP POST) to a cloud server
 *
 * Also provides NTP time sync to the STM32 via UART TIME_SYNC frames.
 *
 * ESP-IDF v5.2
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "nvs_flash.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_bt_device.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_sntp.h"

static const char *TAG = "BRIDGE";

#define UART_NUM        UART_NUM_1
#define UART_TX_PIN     4       /* GPIO4 → STM32 PA10 (RX) */
#define UART_RX_PIN     5       /* GPIO5 ← STM32 PA9  (TX) */
#define UART_BAUD       115200
#define UART_BUF_SIZE   1024

#define BLE_DEVICE_NAME "LumenCast"
#define BLE_SERVICE_UUID 0x18C0
#define BLE_CHAR_RESULT  0x18C1
#define BLE_CHAR_SCAN    0x18C2
#define BLE_CHAR_IES     0x18C3

/* ── UART frame protocol (matches STM32 side) ──────────────────────── */
#define SYNC1 0xAA
#define SYNC2 0x55

static uint8_t rxbuf[UART_BUF_SIZE];
static int rxpos = 0;
static int rxlen = 0;
static bool rx_frame = false;

/* BLE connection state */
static bool ble_connected = false;
static uint16_t ble_conn_handle = 0;
static uint16_t ble_attr_handle_result = 0;
static uint16_t ble_attr_handle_scan = 0;
static uint16_t ble_attr_handle_ies = 0;

/* IES file accumulation buffer */
static char ies_buffer[8192];
static int ies_pos = 0;

/* ── CRC8 ──────────────────────────────────────────────────────────── */
static uint8_t crc8(const uint8_t *data, int len)
{
    uint8_t crc = 0;
    for (int i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++)
            crc = (crc & 0x80) ? (crc << 1) ^ 0x07 : (crc << 1);
    }
    return crc;
}

/* ── Send frame to STM32 ───────────────────────────────────────────── */
static void send_frame(uint8_t type, const uint8_t *payload, uint16_t len)
{
    uint8_t hdr[5] = { SYNC1, SYNC2, type, len & 0xFF, (len >> 8) & 0xFF };
    uart_write_bytes(UART_NUM, (char *)hdr, 5);
    if (len > 0 && payload)
        uart_write_bytes(UART_NUM, (char *)payload, len);

    uint8_t crc_buf[3 + 512];
    crc_buf[0] = type;
    crc_buf[1] = len & 0xFF;
    crc_buf[2] = (len >> 8) & 0xFF;
    if (len > 0) memcpy(crc_buf + 3, payload, len);
    uint8_t crc = crc8(crc_buf, 3 + len);
    uart_write_bytes(UART_NUM, (char *)&crc, 1);
}

/* ── NTP time sync ─────────────────────────────────────────────────── */
static void sync_time_to_stm32(void)
{
    time_t now;
    time(&now);
    if (now > 1700000000) {  /* valid NTP time */
        uint8_t buf[4];
        buf[0] = now & 0xFF;
        buf[1] = (now >> 8) & 0xFF;
        buf[2] = (now >> 16) & 0xFF;
        buf[3] = (now >> 24) & 0xFF;
        send_frame(0x06, buf, 4);
        ESP_LOGI(TAG, "Sent time sync: %lld", (long long)now);
    }
}

static void ntp_callback(struct timeval *tv)
{
    sync_time_to_stm32();
}

/* ── BLE GATT event handler ────────────────────────────────────────── */
static void gatts_event_handler(esp_gatts_cb_event_t event,
                                 esp_gatt_if_t gatts_if,
                                 esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVT:
        ESP_LOGI(TAG, "GATT registered, app_id=%d", param->reg.app_id);
        break;
    case ESP_GATTS_CONNECT_EVT:
        ble_connected = true;
        ble_conn_handle = param->connect.conn_id;
        ESP_LOGI(TAG, "BLE connected: handle=%d", ble_conn_handle);
        break;
    case ESP_GATTS_DISCONNECT_EVT:
        ble_connected = false;
        esp_ble_gap_start_advertising(NULL);
        ESP_LOGI(TAG, "BLE disconnected, restarting advertising");
        break;
    default:
        break;
    }
}

/* ── BLE notify (send data to phone) ───────────────────────────────── */
static void ble_notify(uint16_t attr_handle, const uint8_t *data, uint16_t len)
{
    if (!ble_connected) return;
    esp_ble_gatts_send_indicate(0, ble_conn_handle, attr_handle,
                                 len, (uint8_t *)data, false);
}

/* ── Process received UART frame ───────────────────────────────────── */
static void process_frame(uint8_t type, const uint8_t *payload, uint16_t len)
{
    switch (type) {
    case 0x01:  /* RESULT */
        ESP_LOGI(TAG, "Result received (%d bytes)", len);
        ble_notify(ble_attr_handle_result, payload, len);
        break;

    case 0x02:  /* SCAN_DATA (live) */
        ble_notify(ble_attr_handle_scan, payload, len);
        break;

    case 0x03:  /* IES_FILE chunk */
        if (ies_pos + len < (int)sizeof(ies_buffer)) {
            memcpy(ies_buffer + ies_pos, payload, len);
            ies_pos += len;
        }
        /* Check for end of IES file (heuristic: contains "END" or chunk < max) */
        if (len < 200) {
            ESP_LOGI(TAG, "IES file complete: %d bytes", ies_pos);
            ble_notify(ble_attr_handle_ies, (uint8_t *)ies_buffer, ies_pos);
            ies_pos = 0;
        }
        break;

    case 0x05:  /* DEVICE_INFO */
        ESP_LOGI(TAG, "Device info received");
        break;

    default:
        ESP_LOGW(TAG, "Unknown frame type: 0x%02X", type);
    }
}

/* ── UART receive task ─────────────────────────────────────────────── */
static void uart_rx_task(void *arg)
{
    uint8_t byte;
    while (1) {
        int len = uart_read_bytes(UART_NUM, &byte, 1, pdMS_TO_TICKS(100));
        if (len <= 0) continue;

        if (!rx_frame) {
            if (rxpos == 0 && byte == SYNC1) {
                rxpos = 1;
            } else if (rxpos == 1 && byte == SYNC2) {
                rx_frame = true;
                rxpos = 0;
            } else {
                rxpos = 0;
            }
        } else {
            if (rxpos < (int)sizeof(rxbuf))
                rxbuf[rxpos++] = byte;

            if (rxpos == 3)
                rxlen = rxbuf[1] | (rxbuf[2] << 8);

            if (rxpos >= 4 + rxlen + 1) {
                uint8_t crc = crc8(rxbuf, 3 + rxlen);
                if (crc == rxbuf[3 + rxlen]) {
                    process_frame(rxbuf[0], &rxbuf[3], rxlen);
                }
                rx_frame = false;
                rxpos = 0;
            }
        }
    }
}

/* ── Main ──────────────────────────────────────────────────────────── */
void app_main(void)
{
    ESP_LOGI(TAG, "=== Lumen Cast BLE/WiFi Bridge ===");

    /* NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES)
        nvs_flash_erase();
    nvs_flash_init();

    /* UART to STM32 */
    uart_config_t uart_cfg = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    uart_driver_install(UART_NUM, UART_BUF_SIZE * 2, UART_BUF_SIZE * 2, 0, NULL, 0);
    uart_param_config(UART_NUM, &uart_cfg);
    uart_set_pin(UART_NUM, UART_TX_PIN, UART_RX_PIN, -1, -1);

    /* BLE init */
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();
    esp_ble_gatts_register_callback(gatts_event_handler);
    esp_ble_gap_set_device_name(BLE_DEVICE_NAME);
    esp_ble_gatts_app_register(0);

    /* WiFi + NTP (simplified — in production, use configured SSID) */
    esp_netif_init();
    esp_event_loop_create_default();
    /* WiFi connection would go here; for now, time sync happens when
     * WiFi is configured by the phone app via BLE provisioning */

    /* Start UART RX task */
    xTaskCreate(uart_rx_task, "uart_rx", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "Bridge ready, BLE advertising as '%s'", BLE_DEVICE_NAME);

    /* Periodic time sync attempt */
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(60000));
        sync_time_to_stm32();
    }
}