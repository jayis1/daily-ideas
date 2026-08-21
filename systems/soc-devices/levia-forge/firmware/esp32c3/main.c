/*
 * Levia Forge — ESP32-C3 BLE Bridge Firmware
 *
 * Receives state from RP2040 over UART, exposes it via BLE GATT
 * characteristics, and forwards phone app commands back to the RP2040.
 *
 * Build with ESP-IDF v5.x:
 *   idf.py set-target esp32c3
 *   idf.py flash
 *
 * SPDX-License-Identifier: MIT
 */
#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "nvs_flash.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_bt_defs.h"
#include "esp_log.h"

static const char *TAG = "LEVIA_BLE";

#define UART_NUM        UART_NUM_1
#define UART_TX_PIN     3   /* GPIO3 → RP2040 GP5 (RX) */
#define UART_RX_PIN     2   /* GPIO2 ← RP2040 GP4 (TX) */
#define UART_BAUD       921600
#define UART_BUF_SIZE   1024

/* BLE UUIDs */
#define SERVICE_UUID        0x1800  /* Custom service (placeholder) */
#define CHAR_STATE_UUID     0x2A01
#define CHAR_CMD_UUID       0x2A02
#define CHAR_PATTERN_UUID   0x2A03

/* Global state buffer received from RP2040 */
static char state_buffer[256];
static uint16_t state_len = 0;

/* BLE GATT handles */
static uint16_t gatts_handle_table[3];

/* BLE advertising data */
static esp_ble_adv_data_t adv_data = {
    .set_scan_rsp = false,
    .include_name = true,
    .include_txpower = false,
    .min_interval = 0x0006,
    .max_interval = 0x0010,
    .appearance = 0x00,
    .manufacturer_len = 0,
    .p_manufacturer_data = NULL,
    .service_data_len = 0,
    .p_service_data = NULL,
    .service_uuid_len = 0,
    .p_service_uuid = NULL,
    .flag = (ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT),
};

static esp_ble_adv_params_t adv_params = {
    .adv_int_min = 0x20,
    .adv_int_max = 0x40,
    .adv_type = ADV_TYPE_IND,
    .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
    .channel_map = ADV_CHNL_ALL,
    .adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
};

/* UART receive task */
static void uart_rx_task(void *arg)
{
    uint8_t *data = (uint8_t *)malloc(UART_BUF_SIZE);
    int pos = 0;

    while (1) {
        int len = uart_read_bytes(UART_NUM, data + pos, UART_BUF_SIZE - pos,
                                  pdMS_TO_TICKS(10));
        if (len > 0) {
            for (int i = 0; i < len; i++) {
                if (data[i] == '\n') {
                    /* Complete line received */
                    int line_len = pos + i;
                    if (line_len < sizeof(state_buffer)) {
                        memcpy(state_buffer, data, line_len);
                        state_buffer[line_len] = '\0';
                        state_len = line_len;
                        ESP_LOGV(TAG, "State: %s", state_buffer);
                    }
                    /* Shift remaining data */
                    int remaining = len - i - 1;
                    memmove(data, data + pos + i + 1, remaining);
                    pos = remaining;
                    break;
                }
            }
            if (pos >= UART_BUF_SIZE - 1)
                pos = 0;
        }
    }
    free(data);
    vTaskDelete(NULL);
}

/* Send a command to the RP2040 via UART */
void send_command_to_rp2040(const char *cmd)
{
    uart_write_bytes(UART_NUM, cmd, strlen(cmd));
    uart_write_bytes(UART_NUM, "\n", 1);
}

/* BLE GATT event handler */
static void gatts_event_handler(esp_gatts_cb_event_t event,
                                esp_gatt_if_t gatts_if,
                                esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVT:
        ESP_LOGI(TAG, "GATT registered, app_id=%d", param->reg.app_id);
        esp_ble_gap_config_local_privacy(false);
        break;

    case ESP_GATTS_READ_EVT: {
        /* Phone reads state characteristic → send current state */
        if (param->read.handle == gatts_handle_table[0]) {
            esp_gatt_rsp_t rsp;
            memset(&rsp, 0, sizeof(rsp));
            rsp.attr_value.handle = param->read.handle;
            rsp.attr_value.len = state_len;
            if (state_len > 0 && state_len <= ESP_GATT_MAX_ATTR_LEN) {
                memcpy(rsp.attr_value.value, state_buffer, state_len);
            }
            esp_ble_gatts_send_response(gatts_if, param->read.conn_id,
                                        param->read.trans_id,
                                        ESP_GATT_OK, &rsp);
        }
        break;
    }

    case ESP_GATTS_WRITE_EVT: {
        /* Phone writes command characteristic → forward to RP2040 */
        if (param->write.handle == gatts_handle_table[1]) {
            if (param->write.len > 0 && param->write.len < 200) {
                char cmd[256];
                memcpy(cmd, param->write.value, param->write.len);
                cmd[param->write.len] = '\0';
                ESP_LOGI(TAG, "BLE command: %s", cmd);
                send_command_to_rp2040(cmd);
            }
        }
        break;
    }

    case ESP_GATTS_CONNECT_EVT:
        ESP_LOGI(TAG, "BLE connected, conn_id=%d", param->connect.conn_id);
        esp_ble_gap_stop_advertising();
        break;

    case ESP_GATTS_DISCONNECT_EVT:
        ESP_LOGI(TAG, "BLE disconnected, restarting advertising");
        esp_ble_gap_start_advertising(&adv_params);
        break;

    default:
        break;
    }
}

/* BLE GAP event handler */
static void gap_event_handler(esp_gap_ble_cb_event_t event,
                              esp_ble_gap_cb_param_t *param)
{
    switch (event) {
    case ESP_GAP_BLE_ADV_DATA_SET_EVT:
        esp_ble_gap_start_advertising(&adv_params);
        break;
    default:
        break;
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Levia Forge BLE Bridge starting...");

    /* Initialize NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Initialize UART for RP2040 communication */
    uart_config_t uart_config = {
        .baud_rate = UART_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .source_clk = UART_SCLK_APB,
    };
    uart_driver_install(UART_NUM, UART_BUF_SIZE * 2, UART_BUF_SIZE * 2,
                        0, NULL, 0);
    uart_param_config(UART_NUM, &uart_config);
    uart_set_pin(UART_NUM, UART_TX_PIN, UART_RX_PIN, -1, -1);

    /* Start UART receive task */
    xTaskCreate(uart_rx_task, "uart_rx", 4096, NULL, 5, NULL);

    /* Initialize BLE */
    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();

    /* Set device name */
    esp_ble_gap_set_device_name("Levia Forge");

    /* Register GATT callbacks */
    esp_ble_gatts_register_callback(gatts_event_handler);
    esp_ble_gap_register_callback(gap_event_handler);

    /* Set advertising data */
    esp_ble_gap_config_adv_data(&adv_data);

    ESP_LOGI(TAG, "BLE Bridge ready, advertising as 'Levia Forge'");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}