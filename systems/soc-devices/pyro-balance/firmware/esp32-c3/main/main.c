/*
 * pyro-balance / esp32-c3/main/main.c
 * ESP32-C3 BLE GATT + Wi-Fi captive plotter, UART bridge to STM32.
 * ESP-IDF v5.x
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_wifi.h"
#include "esp_http_server.h"

#define UART_NUM UART_NUM_1
#define STM_TX   10   /* ESP32-C3 RX from STM32 PA9 */
#define STM_RX   9    /* ESP32-C3 TX to STM32 PA10 */
#define BUF_SZ   512

static const char* TAG = "pyro-balance-c3";
static uint8_t uart_buf[BUF_SZ];
static volatile uint16_t uart_avail = 0;

/* BLE service UUIDs */
#define SRVC_UUID 0x1801
#define CHAR_DATA 0x2A01
#define CHAR_CMD   0x2A02

static uint16_t g_conn_id = 0xFFFF;
static uint16_t g_data_handle = 0;

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

static void gap_cb(esp_gap_ble_cb_event_t e, esp_ble_gap_cb_param_t* p) {
    switch (e) {
    case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
        esp_ble_gap_start_advertising(&adv_params);
        break;
    default: break;
    }
}

static void gatts_cb(esp_gatts_cb_event_t e, esp_gatt_if_t g, esp_ble_gatts_cb_param_t* p) {
    switch (e) {
    case ESP_GATTS_CONNECT_EVT:
        g_conn_id = p->connect.conn_id;
        ESP_LOGI(TAG,"BLE connected %d", g_conn_id);
        break;
    case ESP_GATTS_DISCONNECT_EVT:
        g_conn_id = 0xFFFF;
        esp_ble_gap_start_advertising(&adv_params);
        break;
    case ESP_GATTS_WRITE_EVT:
        /* forward command from phone to STM32 over UART */
        uart_write_bytes(UART_NUM, (const char*)p->write.value, p->write.len);
        break;
    default: break;
    }
}

/* UART receive task → BLE notify + Wi-Fi ring buffer */
static void uart_task(void* arg) {
    uart_config_t cfg = {
        .baud_rate = 115200, .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE, .source_clk = UART_SCLK_APB,
    };
    uart_driver_install(UART_NUM, BUF_SZ*2, BUF_SZ*2, 0, NULL, 0);
    uart_param_config(UART_NUM, &cfg);
    uart_set_pin(UART_NUM, STM_RX, STM_TX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    while (1) {
        int len = uart_read_bytes(UART_NUM, uart_buf + uart_avail, BUF_SZ - uart_avail, pdMS_TO_TICKS(20));
        if (len > 0) {
            uart_avail += len;
            /* notify BLE clients with data frames */
            if (g_conn_id != 0xFFFF && g_data_handle) {
                esp_ble_gatts_send_indicate(esp_bt_get_gatts_if_for_profile_id(0),
                    g_conn_id, g_data_handle, uart_avail, uart_buf, false);
            }
            /* also push to Wi-Fi ring buffer (httpd stream) */
            uart_avail = 0;
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

/* Wi-Fi AP + captive portal: simple HTTP endpoint that returns CSV */
static esp_err_t csv_handler(httpd_req_t* req) {
    httpd_resp_set_type(req, "text/csv");
    /* In production: stream last run CSV from SD-over-SPI or buffer.
       For now send a placeholder header. */
    const char* body = "# Pyro Balance live stream (connect BLE for real-time)\n";
    httpd_resp_sendstr(req, body);
    return ESP_OK;
}

static void wifi_init_ap(void) {
    esp_netif_create_default_wifi_ap();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);
    wifi_config_t wc = { .ap = { .ssid = "Pyro-Balance", .ssid_len = 11,
        .channel = 6, .password = "", .max_connection = 2, .authmode = WIFI_AUTH_OPEN } };
    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &wc);
    esp_wifi_start();
}

static void http_init(void) {
    httpd_handle_t s = NULL;
    httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
    if (httpd_start(&s, &cfg) == ESP_OK) {
        httpd_uri_t uri = { .uri = "/tga.csv", .method = HTTP_GET, .handler = csv_handler };
        httpd_register_uri_handler(s, &uri);
    }
}

void app_main(void) {
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    /* BLE */
    esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT);
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();
    esp_ble_gap_register_callback(gap_cb);
    esp_ble_gatts_register_callback(gatts_cb);
    esp_ble_gap_set_device_name("Pyro-Balance");
    esp_ble_gap_config_adv_data(&adv_data);

    /* Wi-Fi AP + HTTP */
    wifi_init_ap();
    http_init();

    /* UART bridge task */
    xTaskCreate(uart_task, "uart", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "Pyro Balance ESP32-C3 ready. BLE: Pyro-Balance  Wi-Fi: Pyro-Balance AP");
}