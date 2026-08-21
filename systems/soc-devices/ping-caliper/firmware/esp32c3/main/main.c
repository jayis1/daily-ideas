/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/main.c — App entry, UART bridge, BLE + Wi-Fi bring-up
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_system.h"
#include "nvs_flash.h"

#include "uart_comm.h"
#include "ble_ndt.h"
#include "wifi_api.h"
#include "led_indicator.h"
#include "button.h"

static const char *TAG = "ping-caliper-c3";

void app_main(void)
{
    ESP_LOGI(TAG, "Ping Caliper ESP32-C3 comms module starting");

    /* NVS init (required for BLE bonding + Wi-Fi) */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
        ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    /* Initialize hardware peripherals */
    led_indicator_init();
    button_init();

    /* UART link to STM32G474 */
    uart_comm_init();

    /* BLE NDT GATT server */
    ble_ndt_init();
    ESP_LOGI(TAG, "BLE advertising as 'PingCaliper'");

    /* Wi-Fi (optional AP for direct phone connection) */
    wifi_api_init();

    /* Main loop: bridge UART <-> BLE, monitor link state */
    led_indicator_set(LED_BLUE, LED_BLINK);
    bool linked = false;
    while (1) {
        bool now_linked = ble_ndt_is_connected();
        if (now_linked != linked) {
            linked = now_linked;
            led_indicator_set(LED_BLUE, linked ? LED_ON : LED_BLINK);
            ESP_LOGI(TAG, "BLE link %s", linked ? "connected" : "lost");
        }
        vTaskDelay(pdMS_TO_TICKS(200));
    }
}