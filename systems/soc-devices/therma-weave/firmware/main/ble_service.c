/*
 * Therma Weave — BLE Service
 * ble_service.c — BLE GATT server for ThermaWeave control
 *
 * SPDX-License-Identifier: MIT
 */

#include "ble_service.h"
#include <string.h>
#include "esp_log.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "BLE_SVC";

static ble_service_t ble;
static uint16_t therma_service_handle;
static uint16_t env_service_handle;

/* Characteristic handles */
static uint16_t char_zone_target_handles[NUM_ZONES];
static uint16_t char_zone_duty_handles[NUM_ZONES];
static uint16_t char_zone_current_handles[NUM_ZONES];
static uint16_t char_activity_handle;
static uint16_t char_enable_handle;
static uint16_t char_safety_handle;
static uint16_t char_fault_handle;
static uint16_t char_pid_handles[3]; /* kp, ki, kd */
static uint16_t char_device_info_handle;

void ble_service_init(void)
{
    ESP_LOGI(TAG, "Initializing BLE service...");

    /* In real firmware:
     * 1. esp_bt_controller_init() + esp_bluedroid_init()
     * 2. esp_ble_gatts_app_register(THERMA_APP_ID)
     * 3. Register GATT event handler
     * 4. Create ThermaWeave service (0xFFB0) with all control characteristics
     * 5. Create Environmental Sensing service (0x181A) with temp/humidity chars
     * 6. Start advertising with manufacturer data
     */

    ble.connected = false;
    ble.conn_handle = 0xFFFF;

    ESP_LOGI(TAG, "BLE service initialized (ThermaWeave UUID 0xFFB0)");
}

void ble_service_set_zone_controllers(zone_controller_t *zones)
{
    ble.zones = zones;
}

void ble_service_set_safety_watchdog(safety_watchdog_t *safety)
{
    ble.safety = safety;
}

void ble_service_task(void *pvParameters)
{
    ESP_LOGI(TAG, "BLE task started");

    while (1) {
        /* In real firmware:
         * - Handle GATT events (ESP_GATTS_WRITE_EVT, ESP_GATTS_READ_EVT)
         * - On write to zone target chars: update zone_controller target_temp
         * - On write to enable char: enable/disable zones
         * - On write to safety char: trigger shutdown or reset
         * - Periodically notify zone data (temp, duty, current) if connected
         */

        if (ble.connected) {
            ble_service_notify_zone_data();
        }

        vTaskDelay(pdMS_TO_TICKS(500));  /* 2 Hz notification rate */
    }
}

void ble_service_notify_zone_data(void)
{
    if (!ble.connected || ble.zones == NULL) return;

    /* In real firmware:
     * esp_ble_gatts_send_indicate() for each notify characteristic:
     *
     * - Zone 0-3 temperature (float32)
     * - Zone 0-3 duty cycle (uint8, 0-100%)
     * - Zone 0-3 current (uint16, mA)
     * - Activity level (uint8)
     * - Fault status (uint8 bitmask)
     */

    /* Build BLE advertising/manufacturer data:
     * [Flags] [16-bit UUID: FFB0] [Mfr-specific: zone0_temp(2), zone0_duty(1), battery(2), fault(1)]
     */
}

/* ========== GATT Event Handler (skeleton) ========== */

static void gatts_event_handler(esp_gatts_cb_event_t event,
                                  esp_gatts_if_t gatts_if,
                                  esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVT:
        ESP_LOGI(TAG, "GATT app registered");
        break;

    case ESP_GATTS_WRITE_EVT: {
        /* Handle writes from BLE client */
        uint16_t handle = param->write.handle;

        /* Zone target temperature writes */
        for (int z = 0; z < NUM_ZONES; z++) {
            if (handle == char_zone_target_handles[z]) {
                if (param->write.len == 1) {
                    uint8_t target = param->write.value[0];
                    zone_controller_set_target(&ble.zones[z], (float)target);
                }
            }
        }

        /* Enable/disable zones */
        if (handle == char_enable_handle) {
            uint8_t bitmask = param->write.value[0];
            for (int z = 0; z < NUM_ZONES; z++) {
                ble.zones[z].enabled = (bitmask >> z) & 1;
            }
        }

        /* Safety shutdown/reset */
        if (handle == char_safety_handle) {
            uint8_t cmd = param->write.value[0];
            if (cmd == 0x01) {
                /* Emergency shutdown all zones */
                for (int z = 0; z < NUM_ZONES; z++) {
                    ble.zones[z].enabled = false;
                    ble.zones[z].duty_pct = 0.0f;
                }
                ESP_LOGW(TAG, "Emergency shutdown via BLE");
            } else if (cmd == 0x02) {
                /* Reset all faults */
                for (int z = 0; z < NUM_ZONES; z++) {
                    zone_controller_reset_faults(&ble.zones[z]);
                }
                ESP_LOGI(TAG, "Fault reset via BLE");
            }
        }

        /* PID parameter writes */
        if (handle == char_pid_handles[0] && param->write.len == 4) {
            float kp;
            memcpy(&kp, param->write.value, 4);
            for (int z = 0; z < NUM_ZONES; z++) ble.zones[z].kp = kp;
        }
        if (handle == char_pid_handles[1] && param->write.len == 4) {
            float ki;
            memcpy(&ki, param->write.value, 4);
            for (int z = 0; z < NUM_ZONES; z++) ble.zones[z].ki = ki;
        }
        if (handle == char_pid_handles[2] && param->write.len == 4) {
            float kd;
            memcpy(&kd, param->write.value, 4);
            for (int z = 0; z < NUM_ZONES; z++) ble.zones[z].kd = kd;
        }
        break;
    }

    case ESP_GATTS_CONNECT_EVT:
        ble.connected = true;
        ble.conn_handle = param->connect.conn_id;
        ESP_LOGI(TAG, "BLE client connected");
        break;

    case ESP_GATTS_DISCONNECT_EVT:
        ble.connected = false;
        ble.conn_handle = 0xFFFF;
        ESP_LOGI(TAG, "BLE client disconnected, restarting advertising");
        /* esp_ble_gap_start_advertising() */
        break;

    default:
        break;
    }
}