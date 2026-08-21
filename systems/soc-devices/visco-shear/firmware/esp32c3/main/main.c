/*
 * visco-shear / firmware / esp32c3 / main / main.c
 * ESP32-C3 companion: UART relay + BLE + Wi-Fi
 *
 * Receives data from RP2040 via UART, relays to BLE GATT + Wi-Fi web UI.
 *
 * MIT License.
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "esp_log.h"

#include "ble_stream.h"
#include "wifi_web.h"

static const char *TAG = "visco-c3";

#define UART_NUM        UART_NUM_1
#define UART_TX_PIN     3
#define UART_RX_PIN     2
#define UART_BAUD       1000000
#define BUF_SIZE        1024

static uint8_t uart_rx_buf[BUF_SIZE];

static void uart_relay_task(void *arg)
{
    esp_log_level_set(TAG, ESP_LOG_INFO);
    ESP_LOGI(TAG, "UART relay task started (baud=%d)", UART_BAUD);

    while (1) {
        int len = uart_read_bytes(UART_NUM, uart_rx_buf, BUF_SIZE, pdMS_TO_TICKS(10));
        if (len > 0) {
            /* Parse frames and relay to BLE/Wi-Fi */
            ble_stream_process_frame(uart_rx_buf, len);
            wifi_web_push_data(uart_rx_buf, len);
        }
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "");
    ESP_LOGI(TAG, "╔══════════════════════════════════╗");
    ESP_LOGI(TAG, "║ Visco Shear ESP32-C3 Companion    ║");
    ESP_LOGI(TAG, "║ BLE 5.0 + Wi-Fi relay             ║");
    ESP_LOGI(TAG, "╚══════════════════════════════════╝");

    /* UART init (RP2040 ↔ ESP32-C3) */
    const uart_config_t uart_cfg = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    ESP_ERROR_CHECK(uart_driver_install(UART_NUM, BUF_SIZE * 2, BUF_SIZE * 2, 0, NULL, 0));
    ESP_ERROR_CHECK(uart_param_config(UART_NUM, &uart_cfg));
    ESP_ERROR_CHECK(uart_set_pin(UART_NUM, UART_TX_PIN, UART_RX_PIN, -1, -1));

    ESP_LOGI(TAG, "UART initialized: TX=%d, RX=%d, baud=%d", UART_TX_PIN, UART_RX_PIN, UART_BAUD);

    /* Init BLE */
    ble_stream_init();
    ESP_LOGI(TAG, "BLE GATT server started");

    /* Init Wi-Fi AP + web server */
    wifi_web_init();
    ESP_LOGI(TAG, "Wi-Fi AP + web server started");

    /* Start UART relay task */
    xTaskCreate(uart_relay_task, "uart_relay", 4096, NULL, 5, NULL);

    ESP_LOGI(TAG, "All systems go. Waiting for RP2040 data...");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}