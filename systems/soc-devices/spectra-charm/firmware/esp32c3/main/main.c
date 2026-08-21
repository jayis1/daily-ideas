/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * ESP32-C3 Firmware — Wireless + UI Controller
 *
 * main.c — Application entry point, WiFi/BLE initialization
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "driver/i2c.h"

#include "ble_spectrum.h"
#include "wifi_api.h"
#include "oled_ui.h"
#include "uart_comm.h"
#include "button.h"
#include "led_indicator.h"

static const char *TAG = "SpectraCharm";

/* GPIO assignments */
#define GPIO_UART_TX    0
#define GPIO_UART_RX    1
#define GPIO_I2C_SDA    2
#define GPIO_I2C_SCL    3
#define GPIO_OLED_RST   4
#define GPIO_CHARGE_STAT 5
#define GPIO_VBUS_DET   6
#define GPIO_USER_BTN   7
#define GPIO_WS2812     8
#define GPIO_BOOT_BTN   9

/* I2C config for OLED */
#define I2C_NUM         I2C_NUM_0
#define I2C_FREQ_HZ     400000
#define OLED_ADDR        0x3C

/* Event queue from buttons / UART */
static QueueHandle_t xEventQueue;

typedef enum {
    EVENT_SCAN_BUTTON,
    EVENT_MODE_BUTTON,
    EVENT_UART_DATA,
    EVENT_LOW_BATTERY,
} EventType_t;

typedef struct {
    EventType_t type;
    uint8_t data[256];
    uint16_t len;
} AppEvent_t;

/* ---- I2C Init ---- */
static void i2c_bus_init(void)
{
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = GPIO_I2C_SDA,
        .scl_io_num = GPIO_I2C_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_FREQ_HZ,
    };
    i2c_param_config(I2C_NUM, &conf);
    i2c_driver_install(I2C_NUM, I2C_MODE_MASTER, 0, 0, 0);
}

/* ---- WiFi Init (AP mode for local API) ---- */
static void wifi_init_ap(void)
{
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    wifi_config_t wifi_config = {
        .ap = {
            .ssid = "SpectraCharm",
            .ssid_len = 12,
            .channel = 6,
            .password = "spectra24",
            .max_connection = 4,
            .authmode = WIFI_AUTH_WPA2_PSK,
        },
    };

    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &wifi_config);
    esp_wifi_start();

    ESP_LOGI(TAG, "WiFi AP started: SpectraCharm");
}

/* ---- BLE Init ---- */
static void ble_init(void)
{
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();

    BLE_Spectrum_Init();
    ESP_LOGI(TAG, "BLE GATT server started");
}

/* ---- Main UI Task ---- */
static void ui_task(void *pvParams)
{
    AppEvent_t event;
    OLEDScreen_t current_screen = SCREEN_HOME;

    OLED_Init(I2C_NUM, OLED_ADDR, GPIO_OLED_RST);
    OLED_ShowSplash();

    vTaskDelay(pdMS_TO_TICKS(2000));
    OLED_ShowScreen(SCREEN_HOME);

    for (;;) {
        if (xQueueReceive(xEventQueue, &event, pdMS_TO_TICKS(100)) == pdTRUE) {
            switch (event.type) {
            case EVENT_SCAN_BUTTON:
                ESP_LOGI(TAG, "Scan button pressed");
                LED_SetColor(LED_COLOR_BLUE);
                OLED_ShowScreen(SCREEN_SCANNING);
                /* Send scan request to STM32 via UART */
                UART_SendScanRequest(SCAN_TYPE_SAMPLE);
                break;

            case EVENT_MODE_BUTTON:
                ESP_LOGI(TAG, "Mode button pressed");
                current_screen = (current_screen + 1) % SCREEN_COUNT;
                OLED_ShowScreen(current_screen);
                break;

            case EVENT_UART_DATA:
                /* Process spectrum data from STM32 */
                ESP_LOGI(TAG, "UART data received, %d bytes", event.len);
                BLE_NotifySpectrum(event.data, event.len);
                OLED_ShowScreen(SCREEN_RESULT);
                LED_SetColor(LED_COLOR_GREEN);
                break;

            case EVENT_LOW_BATTERY:
                OLED_ShowScreen(SCREEN_LOW_BATTERY);
                LED_SetColor(LED_COLOR_RED);
                break;
            }
        }

        /* Update battery indicator on OLED */
        uint8_t battery_pct = 0;
        /* Read battery from STM32 status packet (simplified) */
        OLED_UpdateBattery(battery_pct);
    }
}

/* ---- Button Task ---- */
static void button_task(void *pvParams)
{
    Button_Init(GPIO_USER_BTN, GPIO_BOOT_BTN);
    AppEvent_t event;

    for (;;) {
        if (Button_WaitPress() == BUTTON_SCAN) {
            event.type = EVENT_SCAN_BUTTON;
        } else {
            event.type = EVENT_MODE_BUTTON;
        }
        xQueueSend(xEventQueue, &event, 0);
    }
}

/* ---- UART RX Task ---- */
static void uart_rx_task(void *pvParams)
{
    UART_Init(GPIO_UART_TX, GPIO_UART_RX);
    AppEvent_t event;
    event.type = EVENT_UART_DATA;

    for (;;) {
        /* Block until data from STM32 */
        int len = UART_ReceivePacket(event.data, sizeof(event.data));
        if (len > 0) {
            event.len = len;
            xQueueSend(xEventQueue, &event, 0);
        }
    }
}

/* ---- LED Indicator Task ---- */
static void led_task(void *pvParams)
{
    LED_Init(GPIO_WS2812);

    for (;;) {
        LED_Update();
        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

/* ---- App Main ---- */
void app_main(void)
{
    ESP_LOGI(TAG, "Spectra Charm ESP32-C3 starting...");

    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Create event queue */
    xEventQueue = xQueueCreate(16, sizeof(AppEvent_t));

    /* Initialize peripherals */
    i2c_bus_init();
    wifi_init_ap();
    ble_init();

    /* Start WiFi REST API server */
    WiFi_API_Start();

    /* Create tasks */
    xTaskCreate(ui_task, "ui", 4096, NULL, 5, NULL);
    xTaskCreate(button_task, "btn", 2048, NULL, 4, NULL);
    xTaskCreate(uart_rx_task, "uart", 3072, NULL, 6, NULL);
    xTaskCreate(led_task, "led", 1024, NULL, 1, NULL);

    ESP_LOGI(TAG, "Spectra Charm ready!");
}