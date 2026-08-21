/*
 * Spectra Charm — ESP32-C3 BLE GATT Server for Spectrum Data
 *
 * ble_spectrum.c
 */

#include "ble_spectrum.h"
#include <string.h>
#include "esp_log.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_bt_main.h"

static const char *TAG = "BLE_Spectrum";

/* Service and Characteristic UUIDs */
/* Spectra Charm Service: FEA0 */
#define GATTS_SERVICE_UUID_SPECTRA     0xFEA0
#define GATTS_CHAR_UUID_SCAN_TRIGGER   0xFEA1
#define GATTS_CHAR_UUID_SPECTRUM_DATA  0xFEA2
#define GATTS_CHAR_UUID_COMPOUND_ID    0xFEA3
#define GATTS_CHAR_UUID_BATTERY_LEVEL  0xFEA4
#define GATTS_CHAR_UUID_DEVICE_INFO    0xFEA5

#define GATTS_NUM_APPS        1
#define GATTS_SERVICE_HANDLE  0x00
#define SPECTRUM_MAX_LEN      512

/* GATT attribute handles */
static uint16_t service_handle;
static uint16_t char_scan_trigger_handle;
static uint16_t char_spectrum_data_handle;
static uint16_t char_compound_id_handle;
static uint16_t char_battery_handle;
static uint16_t char_device_info_handle;

/* Connection state */
static bool is_connected = false;
static uint16_t conn_id = 0;

/* Spectrum data buffer for notifications */
static uint8_t spectrum_buf[SPECTRUM_MAX_LEN];
static uint16_t spectrum_len = 0;

/* GATT attribute table */
static esp_gatts_attr_db_t gatt_db[] = {
    /* Service declaration */
    [0] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&primary_service_uuid, ESP_GATT_PERM_READ,
         sizeof(uint16_t), sizeof(GATTS_SERVICE_UUID_SPECTRA),
         (uint8_t *)&GATTS_SERVICE_UUID_SPECTRA, false}
    },

    /* Scan Trigger characteristic (Write) */
    [1] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&character_declaration_uuid, ESP_GATT_PERM_READ,
         sizeof(uint8_t), sizeof(uint8_t),
         (uint8_t *)&char_scan_trigger_handle, false}
    },
    [2] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&char_scan_trigger_handle, ESP_GATT_PERM_WRITE,
         SPECTRUM_MAX_LEN, 1,
         (uint8_t *)"\x00", false}
    },

    /* Spectrum Data characteristic (Notify) */
    [3] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&character_declaration_uuid, ESP_GATT_PERM_READ,
         sizeof(uint8_t), sizeof(uint8_t),
         (uint8_t *)&char_spectrum_data_handle, false}
    },
    [4] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&char_spectrum_data_handle,
         ESP_GATT_PERM_READ | ESP_GATT_PERM_NOTIFY,
         SPECTRUM_MAX_LEN, 0,
         spectrum_buf, false}
    },

    /* Battery Level characteristic (Read) */
    [5] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&character_declaration_uuid, ESP_GATT_PERM_READ,
         sizeof(uint8_t), sizeof(uint8_t),
         (uint8_t *)&char_battery_handle, false}
    },
    [6] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&char_battery_handle, ESP_GATT_PERM_READ,
         sizeof(uint8_t), 1,
         (uint8_t *)"\x64", false} /* 100% default */
    },

    /* Device Info characteristic (Read) */
    [7] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&character_declaration_uuid, ESP_GATT_PERM_READ,
         sizeof(uint8_t), sizeof(uint8_t),
         (uint8_t *)&char_device_info_handle, false}
    },
    [8] = {
        {ESP_GATT_AUTO_RSP},
        {ESP_UUID_LEN_16, (uint8_t *)&char_device_info_handle, ESP_GATT_PERM_READ,
         32, 22,
         (uint8_t *)"Spectra Charm v1.0\0", false}
    },
};

static uint16_t gatt_db_size = sizeof(gatt_db) / sizeof(gatt_db[0]);

/* GAP callback */
static void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param)
{
    switch (event) {
    case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
        ESP_LOGI(TAG, "Adv data set complete");
        break;
    case ESP_GAP_BLE_UPDATE_CONN_PARAMS_EVT:
        ESP_LOGI(TAG, "Connection params updated");
        break;
    default:
        break;
    }
}

/* GATTS callback */
static void gatts_event_handler(esp_gatts_cb_event_t event,
                                  esp_gatt_if_t gatts_if,
                                  esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVT:
        esp_ble_gap_config_adv_data_raw((uint8_t *)"SpectraCharm", 12);
        esp_ble_gatts_create_attr_tab(gatt_db, gatts_if, gatt_db_size, 0);
        break;

    case ESP_GATTS_READ_EVT:
        ESP_LOGI(TAG, "GATT read event");
        break;

    case ESP_GATTS_WRITE_EVT:
        ESP_LOGI(TAG, "GATT write event, handle=%d", param->write.handle);
        if (param->write.handle == char_scan_trigger_handle + 1) {
            /* Scan trigger written — initiate scan */
            uint8_t scan_type = param->write.value[0];
            ESP_LOGI(TAG, "Scan trigger: type=%d", scan_type);
            /* Forward to main task via UART to STM32 */
        }
        break;

    case ESP_GATTS_CONNECT_EVT:
        is_connected = true;
        conn_id = param->connect.conn_id;
        ESP_LOGI(TAG, "BLE connected, conn_id=%d", conn_id);
        break;

    case ESP_GATTS_DISCONNECT_EVT:
        is_connected = false;
        ESP_LOGI(TAG, "BLE disconnected");
        esp_ble_gap_start_advertising(&adv_params);
        break;

    case ESP_GATTS_CREAT_ATTR_TAB_EVT:
        if (param->add_attr_tab.status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Create attr table failed");
        } else {
            ESP_LOGI(TAG, "GATT attr table created");
        }
        break;

    default:
        break;
    }
}

static esp_ble_adv_params_t adv_params = {
    .adv_int_min = 0x0020,
    .adv_int_max = 0x0040,
    .adv_type = ADV_TYPE_IND,
    .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
    .channel_map = ADV_CHNL_ALL,
    .adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
};

void BLE_Spectrum_Init(void)
{
    esp_ble_gap_register_callback(gap_event_handler);
    esp_ble_gatts_register_callback(gatts_event_handler);
    esp_ble_gatts_app_register(0);
    esp_ble_gap_start_advertising(&adv_params);

    ESP_LOGI(TAG, "BLE Spectrum service initialized");
}

void BLE_NotifySpectrum(const uint8_t *data, uint16_t len)
{
    if (!is_connected || len > SPECTRUM_MAX_LEN) return;

    memcpy(spectrum_buf, data, len);
    spectrum_len = len;

    /* Send in 20-byte BLE notification packets */
    uint16_t offset = 0;
    while (offset < len) {
        uint16_t chunk = (len - offset > 20) ? 20 : (len - offset);
        esp_ble_gatts_send_indicate(0, conn_id, char_spectrum_data_handle + 1,
                                     chunk, &spectrum_buf[offset], false);
        offset += chunk;
        vTaskDelay(pdMS_TO_TICKS(10)); /* Rate limit notifications */
    }
}

void BLE_UpdateBattery(uint8_t pct)
{
    /* Update battery characteristic value */
    /* In real firmware, would update the attribute value in the GATT table */
}