/**
 * main.c — ESP32-C3 connectivity MCU for Refracto Bead
 *
 * Receives measurement results from the STM32G491 over UART at 460800 baud,
 * and relays them via BLE GATT and/or Wi-Fi HTTP REST API.
 *
 * The ESP32-C3 is power-gated by the STM32 (PB2/ESP_EN) when no
 * connectivity is needed, saving ~18 mA.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/uart.h"
#include "nvs_flash.h"

#include "uart_protocol.h"
#include "ble_service.h"
#include "wifi_server.h"

static const char *TAG = "refracto_esp32";

#define UART_PORT      UART_NUM_1
#define UART_BAUD      460800
#define UART_RX_PIN    2   /* GPIO2 ← STM32 PA9 (TX) */
#define UART_TX_PIN    3   /* GPIO3 → STM32 PA10 (RX) */
#define UART_BUF_SIZE  1024

void app_main(void) {
    ESP_LOGI(TAG, "Refracto Bead ESP32-C3 starting...");

    /* NVS init */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* UART init (receive from STM32) */
    uart_config_t uart_cfg = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_DEFAULT,
    };
    uart_driver_install(UART_PORT, UART_BUF_SIZE * 2, 0, 0, NULL, 0);
    uart_param_config(UART_PORT, &uart_cfg);
    uart_set_pin(UART_PORT, UART_TX_PIN, UART_RX_PIN,
                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);

    ESP_LOGI(TAG, "UART initialized: %d baud on GPIO2/GPIO3", UART_BAUD);

    /* Initialize BLE */
    ble_service_init();
    ESP_LOGI(TAG, "BLE GATT server started");

    /* Initialize Wi-Fi (optional — only if configured) */
    wifi_server_init();
    ESP_LOGI(TAG, "Wi-Fi HTTP server initialized");

    /* Main task: read UART frames from STM32 and relay */
    uart_protocol_init(UART_PORT);

    uint8_t *data = (uint8_t *)malloc(UART_BUF_SIZE);
    while (1) {
        int len = uart_read_bytes(UART_PORT, data, UART_BUF_SIZE, pdMS_TO_TICKS(100));
        if (len > 0) {
            uart_protocol_process(data, len);
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}