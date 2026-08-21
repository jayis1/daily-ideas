/*
 * esp_bridge.c — ESP32-C3 BLE + Wi-Fi bridge firmware
 *
 * Runs on ESP32-C3-MINI-1 module.
 * Receives data from STM32G474 via UART, forwards to BLE clients
 * and optionally to a Wi-Fi web dashboard.
 *
 * Build with ESP-IDF v5.x or Arduino Core for ESP32.
 * This version targets ESP-IDF.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "nvs_flash.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "driver/gpio.h"

/* BLE includes */
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_bt_defs.h"
#include "esp_gap_bt.h"

/* Wi-Fi includes */
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_http_server.h"

static const char *TAG = "QCM_Halo_BLE";

/* ── Configuration ──────────────────────────────────────── */
#define UART_NUM        UART_NUM_1
#define UART_TX_PIN     2       /* GPIO2 → STM32 RX */
#define UART_RX_PIN     3       /* GPIO3 → STM32 TX */
#define UART_BAUD       921600
#define UART_BUF_SIZE   1024

#define BLE_SERVICE_UUID 0x6E400001
#define BLE_TX_CHAR_UUID 0x6E400002   /* Write (phone → ESP32) */
#define BLE_RX_CHAR_UUID 0x6E400003   /* Notify (ESP32 → phone) */

#define SYNC0 0xA5
#define SYNC1 0x5A

/* ── BLE state ──────────────────────────────────────────── */
static uint16_t gatts_handle_table[3]; /* service, TX, RX */
static bool ble_connected = false;
static uint16_t conn_id = 0;
static uint16_t ble_mtu = 23;

/* RX buffer from STM32 */
static uint8_t uart_rx_buf[UART_BUF_SIZE];
static uint16_t uart_rx_idx = 0;

/* ── CRC8 ───────────────────────────────────────────────── */
static uint8_t crc8(const uint8_t *data, uint16_t len)
{
    uint8_t crc = 0;
    for (uint16_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (uint8_t j = 0; j < 8; j++) {
            crc = (crc & 0x80) ? (crc << 1) ^ 0x07 : (crc << 1);
        }
    }
    return crc;
}

/* ── BLE GATT attributes ────────────────────────────────── */
#define GATTS_APP_ID  0

enum {
    IDX_SVC,
    IDX_TX_CHAR,
    IDX_TX_VAL,
    IDX_RX_CHAR,
    IDX_RX_VAL,
    IDX_COUNT,
};

static esp_gatts_attr_db_t gatts_db[IDX_COUNT] = {
    /* Service */
    [IDX_SVC] = {
        {ESP_GATT_AUTO_RSP},
        {
            {ESP_UUID_LEN_16, (uint8_t *)&(uint16_t){0x2800}, ESP_GATT_PERM_READ,
             sizeof(uint16_t), sizeof(uint16_t), (uint8_t *)&(uint16_t){BLE_SERVICE_UUID}}
        }
    },
    /* TX Characteristic (Write) */
    [IDX_TX_CHAR] = {
        {ESP_GATT_AUTO_RSP},
        {
            {ESP_UUID_LEN_16, (uint8_t *)&(uint16_t){0x2803}, ESP_GATT_PERM_READ,
             sizeof(uint8_t)*7, sizeof(uint8_t)*7, NULL}
        }
    },
    [IDX_TX_VAL] = {
        {ESP_GATT_RSP_BY_APP},
        {
            {ESP_UUID_LEN_128, NULL, ESP_GATT_PERM_WRITE,
             UART_BUF_SIZE, 0, NULL}
        }
    },
    /* RX Characteristic (Notify) */
    [IDX_RX_CHAR] = {
        {ESP_GATT_AUTO_RSP},
        {
            {ESP_UUID_LEN_16, (uint8_t *)&(uint16_t){0x2803}, ESP_GATT_PERM_READ,
             sizeof(uint8_t)*7, sizeof(uint8_t)*7, NULL}
        }
    },
    [IDX_RX_VAL] = {
        {0},
        {
            {ESP_UUID_LEN_128, NULL, 0,
             UART_BUF_SIZE, 0, NULL}
        }
    },
};

/* ── Send data to phone via BLE notify ──────────────────── */
static void ble_notify_data(const uint8_t *data, uint16_t len)
{
    if (!ble_connected) return;

    uint16_t mtu_payload = ble_mtu - 3;
    uint16_t offset = 0;

    while (offset < len) {
        uint16_t chunk = (len - offset > mtu_payload) ? mtu_payload : (len - offset);
        esp_ble_gatts_send_indicate(gatts_handle_table[IDX_SVC], conn_id,
                                     gatts_handle_table[IDX_RX_VAL],
                                     chunk, (uint8_t *)&data[offset], false);
        offset += chunk;
        vTaskDelay(pdMS_TO_TICKS(10)); /* rate limit */
    }
}

/* ── Send command to STM32 ──────────────────────────────── */
static void send_to_stm32(uint8_t cmd, const uint8_t *data, uint16_t len)
{
    uint8_t buf[UART_BUF_SIZE];
    uint16_t idx = 0;
    buf[idx++] = SYNC0;
    buf[idx++] = SYNC1;
    buf[idx++] = cmd;
    buf[idx++] = (uint8_t)len;
    if (data && len > 0)
        memcpy(&buf[idx], data, len);
    idx += len;
    buf[idx++] = crc8(&buf[2], 2 + len);
    uart_write_bytes(UART_NUM, buf, idx);
}

/* ── BLE event handler ──────────────────────────────────── */
static void gatts_event_handler(esp_gatts_cb_event_t event,
                                 esp_ble_gatts_if_t gatts_if,
                                 esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVENT:
        esp_ble_gatts_create_attr_db(gatts_if, gatts_db, GATTS_APP_ID, IDX_COUNT);
        break;
    case ESP_GATTS_CREAT_ATTR_TAB_EVENT:
        if (param->add_attr_tab.status != ESP_GATT_OK) break;
        if (param->add_attr_tab.num_handle != IDX_COUNT) break;
        esp_ble_gatts_start_service(param->add_attr_tab.service_handle);
        gatts_handle_table[IDX_SVC] = param->add_attr_tab.service_handle;
        for (int i = 0; i < IDX_COUNT; i++)
            gatts_handle_table[i] = param->add_attr_tab.handles[i];
        break;
    case ESP_GATTS_CONNECT_EVENT:
        ble_connected = true;
        conn_id = param->connect.conn_id;
        /* Send connection status to STM32 */
        send_to_stm32(0x8C, (uint8_t[]){1}, 1);
        ESP_LOGI(TAG, "BLE client connected");
        break;
    case ESP_GATTS_DISCONNECT_EVENT:
        ble_connected = false;
        send_to_stm32(0x8C, (uint8_t[]){0}, 1);
        esp_ble_gap_start_advertising(&(esp_ble_adv_params_t){
            .adv_int_min = 0x20, .adv_int_max = 0x40,
            .adv_type = ADV_TYPE_IND, .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
            .channel_map = ADV_CHNL_ALL
        });
        ESP_LOGI(TAG, "BLE client disconnected, restarting advertising");
        break;
    case ESP_GATTS_WRITE_EVENT:
        /* Forward command from phone to STM32 */
        if (param->write.handle == gatts_handle_table[IDX_TX_VAL]) {
            /* Parse the frame from the phone */
            uint8_t *data = param->write.value;
            uint16_t len = param->write.len;
            /* Forward raw frame to STM32 (it's already framed) */
            uart_write_bytes(UART_NUM, data, len);
        }
        break;
    case ESP_GATTS_MTU_EVENT:
        ble_mtu = param->mtu.mtu;
        ESP_LOGI(TAG, "MTU: %d", ble_mtu);
        break;
    default:
        break;
    }
}

/* ── GAP event handler ──────────────────────────────────── */
static void gap_event_handler(esp_gap_ble_cb_event_t event,
                               esp_ble_gap_cb_param_t *param)
{
    (void)event; (void)param;
}

/* ── UART → BLE forwarder task ──────────────────────────── */
static void uart_rx_task(void *arg)
{
    uint8_t byte;
    while (1) {
        int len = uart_read_bytes(UART_NUM, &byte, 1, pdMS_TO_TICKS(10));
        if (len <= 0) continue;

        uart_rx_buf[uart_rx_idx++] = byte;

        /* Check for complete frame */
        if (uart_rx_idx >= 5) {
            if (uart_rx_buf[0] == SYNC0 && uart_rx_buf[1] == SYNC1) {
                uint8_t data_len = uart_rx_buf[3];
                uint16_t frame_len = 5 + data_len;
                if (uart_rx_idx >= frame_len) {
                    /* Verify CRC */
                    uint8_t expected = crc8(&uart_rx_buf[2], 2 + data_len);
                    if (uart_rx_buf[4 + data_len] == expected) {
                        /* Forward to BLE */
                        ble_notify_data(uart_rx_buf, frame_len);
                    }
                    /* Reset buffer */
                    uart_rx_idx = 0;
                }
            } else {
                /* Resync */
                uart_rx_idx = 0;
            }
        }

        if (uart_rx_idx >= UART_BUF_SIZE) uart_rx_idx = 0;
    }
}

/* ── Wi-Fi web dashboard (optional) ─────────────────────── */
static httpd_handle_t server = NULL;

static esp_err_t dashboard_handler(httpd_req_t *req)
{
    const char *html = "<!DOCTYPE html><html><head><title>QCM Halo</title>"
        "<meta http-equiv='refresh' content='2'>"
        "<style>body{font-family:sans-serif;margin:20px} "
        "table{border-collapse:collapse} td,th{border:1px solid #ddd;padding:4px}</style>"
        "</head><body><h1>QCM Halo Dashboard</h1>"
        "<p>Live data streaming...</p>"
        "<p>Use the Python live_view.py script for real-time plots.</p>"
        "</body></html>";
    httpd_resp_send(req, html, HTTPD_RESP_USE_STRLEN);
    return ESP_OK;
}

static void start_webserver(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    if (httpd_start(&server, &config) == ESP_OK) {
        httpd_uri_t uri = { .uri = "/", .method = HTTP_GET, .handler = dashboard_handler };
        httpd_register_uri_handler(server, &uri);
        ESP_LOGI(TAG, "Web server started on port 80");
    }
}

/* ── Main ───────────────────────────────────────────────── */
void app_main(void)
{
    /* NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* UART */
    uart_config_t uart_cfg = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(UART_NUM, UART_BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(UART_NUM, &uart_cfg);
    uart_set_pin(UART_NUM, UART_TX_PIN, UART_RX_PIN, -1, -1);

    /* BLE */
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();
    esp_ble_gatts_register_callback(gatts_event_handler);
    esp_ble_gap_register_callback(gap_event_handler);
    esp_ble_gatts_app_register(GATTS_APP_ID);

    /* Set device name */
    esp_ble_gap_set_device_name("QCM Halo");

    /* Start advertising */
    esp_ble_gap_start_advertising(&(esp_ble_adv_params_t){
        .adv_int_min = 0x20, .adv_int_max = 0x40,
        .adv_type = ADV_TYPE_IND, .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
        .channel_map = ADV_CHNL_ALL
    });

    /* Start UART RX task */
    xTaskCreate(uart_rx_task, "uart_rx", 4096, NULL, 5, NULL);

    /* Optionally start Wi-Fi + webserver (commented out for power saving) */
    /* esp_netif_init(); */
    /* esp_event_loop_create_default(); */
    /* start_webserver(); */

    ESP_LOGI(TAG, "QCM Halo BLE bridge started");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}