/**
 * spiro_flow/firmware/esp32_c3_bridge/main.c — ESP32-C3 BLE/WiFi bridge
 *
 * This firmware runs on the ESP32-C3 module that pairs with the CH32V203
 * main MCU. The ESP32-C3 handles wireless connectivity only:
 *   - BLE GATT server for phone app connection
 *   - WiFi client for cloud EHR upload
 *   - NTP time sync → sends to CH32V203 via UART
 *
 * UART protocol: see ble_bridge.c in the main firmware
 *
 * Build: ESP-IDF v5.2
 *   idf.py set-target esp32c3
 *   idf.py build
 *   idf.py -p /dev/ttyUSB0 flash
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
#include "esp_gap_ble.h"
#include "esp_gatts_api.h"
#include "esp_bt_main.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_sntp.h"

static const char *TAG = "BRIDGE";

#define UART_NUM        UART_NUM_1
#define UART_TX_PIN     4   /* GPIO4 → CH32V203 PA10 (RX) */
#define UART_RX_PIN     5   /* GPIO5 ← CH32V203 PA9  (TX) */
#define UART_BAUD       115200
#define BUF_SIZE        1024

#define SYNC1  0xAA
#define SYNC2  0x55

/* BLE service UUIDs */
#define BLE_SERVICE_UUID        0x181A  /* Environmental Sensing Service (repurposed) */
#define BLE_CHAR_RESULT_UUID    0x2A6E  /* Spirometry result characteristic */
#define BLE_CHAR_FLOW_UUID      0x2A6F  /* Flow data characteristic */

/* ── UART receive from CH32V203 ────────────────────────────────────── */

static void uart_rx_task(void *arg)
{
    uint8_t *buf = malloc(BUF_SIZE);
    int len;

    while (1) {
        len = uart_read_bytes(UART_NUM, buf, BUF_SIZE, pdMS_TO_TICKS(100));
        if (len > 0) {
            /* Parse frames and relay to BLE/WiFi */
            ESP_LOGI(TAG, "RX %d bytes from CH32V203", len);
            /* ... frame parsing and BLE notification ... */
        }
    }
    free(buf);
    vTaskDelete(NULL);
}

/* ── NTP time sync ─────────────────────────────────────────────────── */

static void ntp_sync_task(void *arg)
{
    while (1) {
        if (esp_sntp_enabled() && esp_sntp_get_sync_status() == SNTP_SYNC_STATUS_COMPLETED) {
            /* Get current time and send to CH32V203 */
            time_t now = time(NULL);
            uint8_t frame[8];
            frame[0] = SYNC1;
            frame[1] = SYNC2;
            frame[2] = 0x06;  /* TIME_SYNC */
            frame[3] = 4;     /* len lo */
            frame[4] = 0;     /* len hi */
            memcpy(&frame[5], &now, 4);
            frame[9] = 0;     /* CRC placeholder */

            uart_write_bytes(UART_NUM, (char *)frame, sizeof(frame));
            ESP_LOGI(TAG, "Sent time sync: %ld", (long)now);
        }
        vTaskDelay(pdMS_TO_TICKS(60000));  /* sync every 60s */
    }
}

/* ── BLE GATT event handler ────────────────────────────────────────── */

static void gatts_event_handler(esp_gatts_cb_event_t event,
                                 esp_gatt_if_t gatts_if,
                                 esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVT:
        ESP_LOGI(TAG, "GATT server registered, app_id=%d", param->reg.app_id);
        break;
    case ESP_GATTS_CONNECT_EVT:
        ESP_LOGI(TAG, "Client connected, conn_id=%d", param->connect.conn_id);
        break;
    case ESP_GATTS_DISCONNECT_EVT:
        ESP_LOGI(TAG, "Client disconnected");
        break;
    default:
        break;
    }
}

/* ── Main ──────────────────────────────────────────────────────────── */

void app_main(void)
{
    ESP_LOGI(TAG, "=== Spiro Flow BLE/WiFi Bridge (ESP32-C3) ===");

    /* NVS init */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* UART init for CH32V203 communication */
    uart_config_t uart_cfg = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(UART_NUM, BUF_SIZE * 2, BUF_SIZE * 2, 0, NULL, 0);
    uart_param_config(UART_NUM, &uart_cfg);
    uart_set_pin(UART_NUM, UART_TX_PIN, UART_RX_PIN,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    /* BLE init */
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();
    esp_ble_gatts_register_callback(gatts_event_handler);

    /* WiFi init (station mode) */
    /* esp_netif_init();
     * esp_event_loop_create_default();
     * esp_netif_create_sta_wifi();
     * esp_wifi_set_config(WIFI_IF_STA, &wifi_config);
     * esp_wifi_start();
     */

    /* SNTP init */
    /* esp_sntp_setoperatingmode(SNTP_OPMODE_POLL);
     * esp_sntp_setservername(0, "pool.ntp.org");
     * esp_sntp_init();
     */

    ESP_LOGI(TAG, "Bridge initialized. Starting tasks...");

    xTaskCreate(uart_rx_task, "uart_rx", 4096, NULL, 5, NULL);
    xTaskCreate(ntp_sync_task, "ntp_sync", 2048, NULL, 3, NULL);
}