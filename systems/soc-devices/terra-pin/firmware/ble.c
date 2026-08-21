/**
 * terra_pin/ble.c — BLE GATT server for soil health notifications
 *
 * Exposes a GATT service with characteristics for SHI, flux, ORP, EC,
 * moisture, temperature, raw CO2, and mode control.
 *
 * Uses ESP-IDF Bluedroid stack.
 */

#include "main.h"
#include "esp_log.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_bt_device.h"
#include <string.h>

static const char *TAG = "BLE";

#define GATTS_SERVICE_TAG_TERRA   0x01
#define GATTS_NUM_HANDLE_TERRA    12

/* UUIDs (128-bit, custom) */
static uint8_t terra_service_uuid128[] = {
    0xFB,0x34,0x9B,0x5F,0x80,0x00,0x00,0x80,
    0x80,0x00,0x00,0x10,0x00,0x00,0x00,0x01
};

static uint8_t terra_char_uuid128[][16] = {
    [0x02] = {0xFB,0x34,0x9B,0x5F,0x80,0x00,0x00,0x80,0x80,0x00,0x00,0x10,0x00,0x00,0x00,0x02},
    [0x03] = {0xFB,0x34,0x9B,0x5F,0x80,0x00,0x00,0x80,0x80,0x00,0x00,0x10,0x00,0x00,0x00,0x03},
    [0x04] = {0xFB,0x34,0x9B,0x5F,0x80,0x00,0x00,0x80,0x80,0x00,0x00,0x10,0x00,0x00,0x00,0x04},
    [0x05] = {0xFB,0x34,0x9B,0x5F,0x80,0x00,0x00,0x80,0x80,0x00,0x00,0x10,0x00,0x00,0x00,0x05},
    [0x06] = {0xFB,0x34,0x9B,0x5F,0x80,0x00,0x00,0x80,0x80,0x00,0x00,0x10,0x00,0x00,0x00,0x06},
    [0x07] = {0xFB,0x34,0x9B,0x5F,0x80,0x00,0x00,0x80,0x80,0x00,0x00,0x10,0x00,0x00,0x00,0x07},
    [0x08] = {0xFB,0x34,0x9B,0x5F,0x80,0x00,0x00,0x80,0x80,0x00,0x00,0x10,0x00,0x00,0x00,0x08},
    [0x09] = {0xFB,0x34,0x9B,0x5F,0x80,0x00,0x00,0x80,0x80,0x00,0x00,0x10,0x00,0x00,0x00,0x09},
};

static uint16_t g_handle_table[10];
static bool g_connected = false;
static uint16_t g_conn_id = 0;

/* Advertising data */
static esp_ble_adv_data_t adv_data = {
    .set_scan_rsp = false,
    .include_name = true,
    .include_txpower = false,
    .min_interval = 0x20,
    .max_interval = 0x40,
    .appearance = 0x00,
    .manufacturer_len = 0,
    .service_data_len = 0,
    .service_uuid_len = 16,
    .p_service_uuid = terra_service_uuid128,
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

static void gap_event_handler(esp_gap_ble_cb_event_t event,
                               esp_ble_gap_event_param_t *param)
{
    switch (event) {
    case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
        esp_ble_gap_start_advertising(&adv_params);
        break;
    case ESP_GAP_BLE_ADV_START_COMPLETE_EVT:
        ESP_LOGI(TAG, "BLE advertising started");
        break;
    case ESP_GAP_BLE_UPDATE_CONN_PARAMS_EVT:
        break;
    default:
        break;
    }
}

/* Latest reading snapshot for read responses */
static terra_reading_t g_last_reading;

static void gatts_event_handler(esp_gatts_cb_event_t event,
                                 esp_gatt_if_t gatts_if,
                                 esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVT:
        if (param->reg.status == ESP_GATT_OK) {
            esp_ble_gap_set_device_name("Terra Pin");
            esp_ble_gap_config_adv_data(&adv_data);
            esp_ble_gatts_create_attr_db(gatts_if, NULL, 0);
        }
        break;
    case ESP_GATTS_CONNECT_EVT:
        g_connected = true;
        g_conn_id = param->connect.conn_id;
        ESP_LOGI(TAG, "BLE connected");
        break;
    case ESP_GATTS_DISCONNECT_EVT:
        g_connected = false;
        esp_ble_gap_start_advertising(&adv_params);
        ESP_LOGI(TAG, "BLE disconnected, re-advertising");
        break;
    case ESP_GATTS_READ_EVT: {
        /* Return latest reading data based on handle */
        uint16_t handle = param->read.handle;
        uint8_t value[8];
        int len = 0;
        memset(value, 0, sizeof(value));

        if (handle == g_handle_table[0x02]) { /* SHI */
            value[0] = g_last_reading.shi;
            len = 1;
        } else if (handle == g_handle_table[0x03]) { /* Flux float32 */
            memcpy(value, &g_last_reading.flux_mgC, 4);
            len = 4;
        } else if (handle == g_handle_table[0x04]) { /* ORP int16 */
            memcpy(value, &g_last_reading.orp_mv, 2);
            len = 2;
        } else if (handle == g_handle_table[0x05]) { /* EC uint16 */
            memcpy(value, &g_last_reading.ec_us, 2);
            len = 2;
        } else if (handle == g_handle_table[0x06]) { /* Moisture float32 */
            memcpy(value, &g_last_reading.moisture_vwc, 4);
            len = 4;
        } else if (handle == g_handle_table[0x07]) { /* Temp float32 */
            memcpy(value, &g_last_reading.temp_c, 4);
            len = 4;
        }
        esp_ble_gatts_send_response(gatts_if, param->read.conn_id,
                                    param->read.trans_id, ESP_GATT_OK,
                                    (esp_gatt_rsp_t *)&value);
        break;
    }
    default:
        break;
    }
}

esp_err_t ble_init(void)
{
    ESP_LOGI(TAG, "Initializing BLE");

    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_err_t ret = esp_bt_controller_init(&bt_cfg);
    if (ret != ESP_OK) return ret;
    ret = esp_bt_controller_enable(ESP_BT_MODE_BLE);
    if (ret != ESP_OK) return ret;
    ret = esp_bluedroid_init();
    if (ret != ESP_OK) return ret;
    ret = esp_bluedroid_enable();
    if (ret != ESP_OK) return ret;

    esp_ble_gap_register_callback(gap_event_handler);
    esp_ble_gatts_register_callback(gatts_event_handler);
    esp_ble_gatts_app_register(GATTS_SERVICE_TAG_TERRA);

    ESP_LOGI(TAG, "BLE initialized");
    return ESP_OK;
}

void ble_notify_reading(const terra_reading_t *r)
{
    memcpy(&g_last_reading, r, sizeof(g_last_reading));
    if (!g_connected) return;

    /* Send SHI notification if subscribed */
    uint8_t shi_val = r->shi;
    esp_ble_gatts_send_indicate(0, g_conn_id, g_handle_table[0x02],
                                1, &shi_val, false);
    ESP_LOGI(TAG, "BLE notified: SHI=%d", r->shi);
}