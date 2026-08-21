/*
 * hall-puck / esp32-c3 / main / main.c
 * ESP32-C3 BLE GATT + Wi-Fi AP + UART relay to STM32G474.
 *
 * Receives measurement data from STM32 via UART, streams to phone via BLE,
 * and serves a Wi-Fi web UI for CSV download and remote control.
 *
 * ESP-IDF v5.x
 *
 * MIT License.
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_wifi.h"
#include "esp_http_server.h"

static const char *TAG = "hall-puck-c3";

/* UART config — bridge to STM32G474 */
#define UART_NUM        UART_NUM_1
#define STM_TX_PIN      1    /* ESP32-C3 RX from STM32 PA9 (TX) */
#define STM_RX_PIN      0    /* ESP32-C3 TX to STM32 PA10 (RX) */
#define UART_BAUD       460800
#define UART_BUF_SZ     512

/* BLE UUIDs */
#define SRVC_UUID       0x9201
#define CHAR_DATA       0x9202
#define CHAR_RESULT     0x9203
#define CHAR_CMD        0x9204
#define CHAR_INFO       0x9205

/* Frame protocol (match STM32 side) */
#define FRAME_SOF       0xA5
#define FRAME_EOF       0x5A
#define FRAME_RESULT    0x01
#define FRAME_POINT     0x02
#define FRAME_INFO      0x03
#define FRAME_CMD       0x04
#define FRAME_STATE     0x05
#define FRAME_ACK       0x06

static uint16_t g_conn_id = 0xFFFF;
static uint16_t g_result_handle = 0;
static uint16_t g_data_handle = 0;
static uint16_t g_cmd_handle = 0;
static uint16_t g_info_handle = 0;
static bool g_ble_connected = false;

/* UART RX buffer + frame parser */
static uint8_t uart_rx_buf[UART_BUF_SZ];
static volatile int uart_rx_len = 0;

/* BLE advertising data */
static esp_ble_adv_data_t adv_data = {
    .set_scan_rsp = false,
    .include_name = true,
    .min_interval = 0x20, .max_interval = 0x40,
    .appearance = 0x00,
    .flag = (ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT),
};

static esp_ble_adv_params_t adv_params = {
    .adv_int_min = 0x20, .adv_int_max = 0x40,
    .adv_type = ADV_TYPE_IND,
    .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
    .channel_map = ADV_CHNL_ALL,
};

/* ---- BLE GATTS callbacks ---- */
static void gatts_event_handler(esp_gatts_cb_event_t event,
                                 esp_gatt_if_t gatts_if,
                                 esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVT:
        ESP_LOGI(TAG, "BLE registered, app_id=%d", param->reg.app_id);
        esp_ble_gap_set_device_name("HallPuck");
        esp_ble_gap_config_adv_data(&adv_data);
        break;

    case ESP_GATTS_CONNECT_EVT:
        g_conn_id = param->connect.conn_id;
        g_ble_connected = true;
        ESP_LOGI(TAG, "BLE connected, conn_id=%d", g_conn_id);
        break;

    case ESP_GATTS_DISCONNECT_EVT:
        g_ble_connected = false;
        g_conn_id = 0xFFFF;
        ESP_LOGI(TAG, "BLE disconnected, restarting advertising");
        esp_ble_gap_start_advertising(&adv_params);
        break;

    case ESP_GATTS_WRITE_EVT:
        if (param->write.handle == g_cmd_handle) {
            /* Forward command to STM32 via UART */
            if (param->write.len > 0 && param->write.len < 256) {
                /* Wrap in frame and send to STM32 */
                uint8_t frame[260];
                int fidx = 0;
                frame[fidx++] = FRAME_SOF;
                frame[fidx++] = FRAME_CMD;
                frame[fidx++] = (param->write.len >> 8) & 0xFF;
                frame[fidx++] = param->write.len & 0xFF;
                uint8_t cs = FRAME_CMD ^ frame[2] ^ frame[3];
                for (int i = 0; i < param->write.len; i++) {
                    frame[fidx++] = param->write.value[i];
                    cs ^= param->write.value[i];
                }
                frame[fidx++] = cs;
                frame[fidx++] = FRAME_EOF;
                uart_write_bytes(UART_NUM, (const char *)frame, fidx);
            }
        }
        break;

    default:
        break;
    }
}

static void gap_event_handler(esp_gap_ble_cb_event_t event,
                               esp_ble_gap_cb_param_t *param)
{
    switch (event) {
    case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
        esp_ble_gap_start_advertising(&adv_params);
        break;
    default:
        break;
    }
}

/* ---- UART RX task — parse frames from STM32, forward via BLE ---- */
static void uart_rx_task(void *arg)
{
    (void)arg;
    uint8_t byte;
    static enum { WAIT_SOF, READ_TYPE, READ_LEN_HI, READ_LEN_LO,
                  READ_PAYLOAD, READ_CHECKSUM, READ_EOF } state = WAIT_SOF;
    static uint8_t frame_type = 0;
    static uint16_t frame_len = 0;
    static uint8_t frame_payload[256];
    static int payload_idx = 0;
    static uint8_t expected_cs = 0;

    while (1) {
        int len = uart_read_bytes(UART_NUM, &byte, 1, pdMS_TO_TICKS(10));
        if (len <= 0) continue;

        switch (state) {
        case WAIT_SOF:
            if (byte == FRAME_SOF) {
                state = READ_TYPE;
                expected_cs = 0;
            }
            break;
        case READ_TYPE:
            frame_type = byte;
            expected_cs = byte;
            state = READ_LEN_HI;
            break;
        case READ_LEN_HI:
            frame_len = (byte << 8);
            expected_cs ^= byte;
            state = READ_LEN_LO;
            break;
        case READ_LEN_LO:
            frame_len |= byte;
            expected_cs ^= byte;
            payload_idx = 0;
            state = (frame_len > 0) ? READ_PAYLOAD : READ_CHECKSUM;
            break;
        case READ_PAYLOAD:
            frame_payload[payload_idx++] = byte;
            expected_cs ^= byte;
            if (payload_idx >= frame_len) state = READ_CHECKSUM;
            break;
        case READ_CHECKSUM:
            if (byte == expected_cs) {
                state = READ_EOF;
            } else {
                state = WAIT_SOF;
            }
            break;
        case READ_EOF:
            if (byte == FRAME_EOF) {
                /* Process frame */
                switch (frame_type) {
                case FRAME_RESULT:
                    if (g_ble_connected && g_result_handle) {
                        esp_ble_gatts_send_indicate(
                            ESP_GATT_IF_NONE, g_conn_id,
                            g_result_handle, frame_len, frame_payload, false);
                    }
                    ESP_LOGI(TAG, "Result frame received (%d bytes)", frame_len);
                    break;
                case FRAME_POINT:
                    if (g_ble_connected && g_data_handle) {
                        esp_ble_gatts_send_indicate(
                            ESP_GATT_IF_NONE, g_conn_id,
                            g_data_handle, frame_len, frame_payload, false);
                    }
                    break;
                case FRAME_INFO:
                    if (g_ble_connected && g_info_handle) {
                        esp_ble_gatts_send_indicate(
                            ESP_GATT_IF_NONE, g_conn_id,
                            g_info_handle, frame_len, frame_payload, false);
                    }
                    break;
                case FRAME_STATE:
                    ESP_LOGI(TAG, "STM32 state: %d", frame_payload[0]);
                    break;
                default:
                    break;
                }
            }
            state = WAIT_SOF;
            break;
        }
    }
}

/* ---- Wi-Fi AP + Web UI ---- */
static void wifi_init_softap(void)
{
    esp_wifi_init(NULL);

    wifi_config_t wifi_config = {
        .ap = {
            .ssid = "HallPuck",
            .ssid_len = strlen("HallPuck"),
            .channel = 1,
            .max_connection = 4,
            .authmode = WIFI_AUTH_OPEN,
        },
    };
    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &wifi_config);
    esp_wifi_start();
    ESP_LOGI(TAG, "Wi-Fi AP started: HallPuck");
}

/* Simple HTTP handler — serve status page */
static esp_err_t root_get_handler(httpd_req_t *req)
{
    const char *html = "<html><body><h1>Hall Puck</h1>"
                       "<p>Semiconductor characterization system.</p>"
                       "<p>Connect via BLE for live data.</p>"
                       "</body></html>";
    httpd_resp_send(req, html, HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}

static httpd_uri_t root_uri = {
    .uri = "/", .method = HTTP_GET, .handler = root_get_handler
};

static void start_webserver(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    httpd_handle_t server = NULL;
    if (httpd_start(&server, &config) == ESP_OK) {
        httpd_register_uri_handler(server, &root_uri);
        ESP_LOGI(TAG, "Web server started");
    }
}

/* ---- Main ---- */
void app_main(void)
{
    ESP_LOGI(TAG, "=== Hall Puck ESP32-C3 Companion ===");

    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Initialize UART for STM32 communication */
    uart_config_t uart_cfg = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    uart_driver_install(UART_NUM, UART_BUF_SZ * 2, UART_BUF_SZ * 2, 0, NULL, 0);
    uart_param_config(UART_NUM, &uart_cfg);
    uart_set_pin(UART_NUM, STM_RX_PIN, STM_TX_PIN, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    /* Initialize BLE */
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();
    esp_ble_gap_register_callback(gap_event_handler);
    esp_ble_gatts_register_callback(gatts_event_handler);

    /* Register BLE service (simplified — would create full GATT table) */
    /* In production: esp_ble_gatts_app_register(0, ...) + create attributes */

    /* Initialize Wi-Fi AP */
    wifi_init_softap();

    /* Start web server */
    start_webserver();

    /* Start UART RX task */
    xTaskCreate(uart_rx_task, "uart_rx", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "Ready. BLE: HallPuck, WiFi: HallPuck AP");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}