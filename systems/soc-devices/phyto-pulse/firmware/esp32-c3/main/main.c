/*
 * main.c — ESP32-C3 connectivity MCU firmware
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Receives samples + events from STM32G474 over UART @ 460800.
 * Serves live waveform + event stream over BLE 5.0 GATT + Wi-Fi WebSocket.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_system.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_bt_device.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "lwip/sockets.h"
#include "driver/uart.h"

#include "ble_service.h"
#include "wifi_server.h"
#include "uart_protocol.h"

static const char *TAG = "phyto-pulse";

void app_main(void)
{
    ESP_LOGI(TAG, "Phyto Pulse ESP32-C3 starting...");

    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Initialize UART protocol (receives from STM32) */
    uart_protocol_init();

    /* Initialize BLE GATT server */
    ble_service_init();

    /* Initialize Wi-Fi AP + WebSocket server */
    wifi_server_init();

    /* Main task: route data from UART to BLE/Wi-Fi */
    xTaskCreate(uart_protocol_task, "uart_rx", 4096, NULL, 5, NULL);
    xTaskCreate(ble_notify_task, "ble_notify", 2048, NULL, 4, NULL);
    xTaskCreate(wifi_ws_task, "wifi_ws", 4096, NULL, 3, NULL);

    ESP_LOGI(TAG, "All tasks started. BLE+WiFi ready.");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        /* Periodic status broadcast */
        ble_service_send_status();
    }
}