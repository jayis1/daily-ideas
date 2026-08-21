/* ble.c — BLE GATT server for Taste Bead
 *
 * Implements a BLE 5.0 GATT server with characteristics for:
 *   - Result notifications (classification results)
 *   - Spectrum notifications (raw impedance data, chunked)
 *   - Command writes (from phone app)
 *   - Library management (list/add/delete entries)
 *   - Status notifications
 *
 * Uses the ESP-IDF Bluedroid stack (not NimBLE) for GATT server support.
 */

#include "ble.h"
#include "sdkconfig.h"
#include "esp_log.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_bt_device.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "ble";

#define GATTS_SERVICE_UUID   0xF00D
#define GATTS_NUM_APPS       1
#define GATTS_CHAR_NUM       5

/* Characteristic UUIDs (16-bit short UUIDs for simplicity) */
#define CHAR_UUID_RESULT     0xF001
#define CHAR_UUID_SPECTRUM   0xF002
#define CHAR_UUID_COMMAND    0xF003
#define CHAR_UUID_LIBRARY    0xF004
#define CHAR_UUID_STATUS     0xF005

/* GATT handles */
static uint16_t g_gatt_if = 0;
static uint16_t g_conn_id = 0;
static bool g_connected = false;
static uint16_t g_handle_table[6] = {0};

/* Command queue (for app_main to poll) */
static uint8_t g_cmd_buf[64];
static int g_cmd_len = 0;
static uint8_t g_cmd_opcode = 0;
static volatile bool g_cmd_ready = false;

/* Advertising data */
static esp_ble_adv_data_t adv_data = {
    .set_scan_rsp = false,
    .include_name = true,
    .include_txpower = false,
    .min_interval = 0x20,
    .max_interval = 0x40,
    .appearance = 0x00,
    .manufacturer_len = 0,
    .p_manufacturer_data = NULL,
    .service_data_len = 0,
    .p_service_data = NULL,
    .service_uuid_len = 2,
    .p_service_uuid = (uint8_t[]){0x0D, 0xF0}, /* 0xF00D little-endian */
    .flag = ESP_BLE_ADV_FLAG_GEN_DISC | ESP_BLE_ADV_FLAG_BREDR_NOT_SPT,
};

static esp_ble_adv_params_t adv_params = {
    .adv_int_min = 0x20,
    .adv_int_max = 0x40,
    .adv_type = ADV_TYPE_IND,
    .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
    .channel_map = ADV_CHNL_ALL,
    .adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
};

/* GATT attribute table */
static esp_gatts_attr_db_t gatt_db[GATTS_CHAR_NUM * 3 + 1] = {
    /* Service declaration */
    [0] = { {ESP_GATT_AUTO_RSP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x00, 0x18}, ESP_GATT_PERM_READ,
             2, (uint8_t[]){0x0D, 0xF0}, 2} },

    /* Characteristic: Result (notify) */
    [1] = { {ESP_GATT_AUTO_RSP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x03, 0x28}, ESP_GATT_PERM_READ,
             8, (uint8_t[]){0x01, 0xF0, 0x10, 0x00, 0x01, 0x00, 0x00, 0x00}, 8} },
    [2] = { {ESP_GATT_RSP_BY_APP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x01, 0xF0}, ESP_GATT_PERM_READ,
             0, NULL, 0} },

    /* Characteristic: Spectrum (notify) */
    [3] = { {ESP_GATT_AUTO_RSP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x03, 0x28}, ESP_GATT_PERM_READ,
             8, (uint8_t[]){0x02, 0xF0, 0x10, 0x00, 0x01, 0x00, 0x00, 0x00}, 8} },
    [4] = { {ESP_GATT_RSP_BY_APP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x02, 0xF0}, ESP_GATT_PERM_READ,
             0, NULL, 0} },

    /* Characteristic: Command (write) */
    [5] = { {ESP_GATT_AUTO_RSP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x03, 0x28}, ESP_GATT_PERM_READ,
             8, (uint8_t[]){0x03, 0xF0, 0x08, 0x00, 0x01, 0x00, 0x00, 0x00}, 8} },
    [6] = { {ESP_GATT_AUTO_RSP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x03, 0xF0},
             ESP_GATT_PERM_WRITE | ESP_GATT_PERM_READ, 64, NULL, 0} },

    /* Characteristic: Library (read+notify) */
    [7] = { {ESP_GATT_AUTO_RSP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x03, 0x28}, ESP_GATT_PERM_READ,
             8, (uint8_t[]){0x04, 0xF0, 0x12, 0x00, 0x01, 0x00, 0x00, 0x00}, 8} },
    [8] = { {ESP_GATT_RSP_BY_APP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x04, 0xF0}, ESP_GATT_PERM_READ,
             0, NULL, 0} },

    /* Characteristic: Status (notify) */
    [9] = { {ESP_GATT_AUTO_RSP},
            {ESP_UUID_LEN_16, (uint8_t[]){0x03, 0x28}, ESP_GATT_PERM_READ,
             8, (uint8_t[]){0x05, 0xF0, 0x10, 0x00, 0x01, 0x00, 0x00, 0x00}, 8} },
    [10] = { {ESP_GATT_RSP_BY_APP},
             {ESP_UUID_LEN_16, (uint8_t[]){0x05, 0xF0}, ESP_GATT_PERM_READ,
              0, NULL, 0} },
};

/* GATT event handler */
static void gatts_event_handler(esp_gatts_cb_event_t event,
                                  esp_gatt_if_t gatts_if,
                                  esp_ble_gatts_cb_param_t *param)
{
    switch (event) {
    case ESP_GATTS_REG_EVT:
        ESP_LOGI(TAG, "GATT registered, app_if=%d", gatts_if);
        g_gatt_if = gatts_if;
        esp_ble_gatts_create_attr_tab(gatts_if, gatt_db,
                                       GATTS_SERVICE_UUID, GATTS_NUM_APPS);
        break;

    case ESP_GATTS_CREAT_ATTR_TAB_EVT:
        if (param->add_attr_tab.status != ESP_GATT_OK) {
            ESP_LOGE(TAG, "Attr table create failed: %d",
                     param->add_attr_tab.status);
        } else {
            memcpy(g_handle_table, param->add_attr_tab.handles,
                   sizeof(g_handle_table));
            esp_ble_gatts_start_service(g_handle_table[0]);
            ESP_LOGI(TAG, "GATT service started");
        }
        break;

    case ESP_GATTS_CONNECT_EVT:
        g_conn_id = param->connect.conn_id;
        g_connected = true;
        ESP_LOGI(TAG, "BLE client connected (conn_id=%d)", g_conn_id);
        esp_ble_gap_stop_advertising();
        break;

    case ESP_GATTS_DISCONNECT_EVT:
        g_connected = false;
        ESP_LOGI(TAG, "BLE client disconnected");
        esp_ble_gap_start_advertising(&adv_params);
        break;

    case ESP_GATTS_WRITE_EVT:
        if (param->write.handle == g_handle_table[6]) {
            /* Command characteristic write */
            if (param->write.len > 0 && param->write.len <= sizeof(g_cmd_buf)) {
                g_cmd_opcode = param->write.value[0];
                memcpy(g_cmd_buf, param->write.value + 1,
                       param->write.len - 1);
                g_cmd_len = param->write.len - 1;
                g_cmd_ready = true;
                ESP_LOGI(TAG, "Command received: 0x%02X (%d bytes)",
                         g_cmd_opcode, g_cmd_len);
            }
        }
        break;

    case ESP_GATTS_READ_EVT:
        /* App will handle reads for spectrum/library */
        break;

    default:
        break;
    }
}

/* GAP event handler */
static void gap_event_handler(esp_gap_ble_cb_event_t event,
                               esp_ble_gap_cb_param_t *param)
{
    switch (event) {
    case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
        esp_ble_gap_start_advertising(&adv_params);
        break;
    default:
        break;
    }
}

esp_err_t ble_init(void)
{
    /* Initialize Bluedroid */
    esp_err_t ret = esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BT controller mem release failed: %s",
                 esp_err_to_name(ret));
        return ret;
    }

    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    ret = esp_bt_controller_init(&bt_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BT controller init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_bt_controller_enable(ESP_BT_MODE_BLE);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BT controller enable failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_bluedroid_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Bluedroid init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_bluedroid_enable();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Bluedroid enable failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Set device name */
    esp_ble_gap_set_device_name("Taste Bead");

    /* Register GAP/GATTS callbacks */
    esp_ble_gap_register_callback(gap_event_handler);
    esp_ble_gatts_register_callback(gatts_event_handler);

    /* Register GATT app */
    esp_ble_gatts_app_register(0);

    /* Set advertising data */
    esp_ble_gap_config_adv_data(&adv_data);

    ESP_LOGI(TAG, "BLE initialized (device: Taste Bead)");
    return ESP_OK;
}

esp_err_t ble_send_result(const ble_result_t *result)
{
    if (!g_connected) return ESP_ERR_INVALID_STATE;

    /* Pack result into a notification: [type:1][label:32][confidence:4][dist:4][ts:8] */
    uint8_t buf[50] = {0};
    buf[0] = BLE_MSG_RESULT;
    memcpy(buf + 1, result->label, 32);
    memcpy(buf + 33, &result->confidence, 4);
    memcpy(buf + 37, &result->distance, 4);
    memcpy(buf + 41, &result->timestamp_us, 8);
    buf[49] = 0;

    esp_ble_gatts_send_indicate(g_gatt_if, g_conn_id,
                                 g_handle_table[2], sizeof(buf), buf, false);
    return ESP_OK;
}

esp_err_t ble_send_spectrum(const eis_result_t *eis)
{
    if (!g_connected) return ESP_ERR_INVALID_STATE;

    /* Spectrum is 5×20×(4+4) = 800 bytes — chunk into 20-byte BLE packets */
    /* Each packet: [seq:1][electrode:1][freq_idx:1][z_mag:4][z_phase:4][crc:1] = 12 bytes */
    uint8_t buf[20];
    int seq = 0;
    for (int e = 0; e < NUM_ELECTRODES; e++) {
        for (int f = 0; f < NUM_FREQS; f++) {
            buf[0] = BLE_MSG_SPECTRUM;
            buf[1] = seq++;
            buf[2] = e;
            buf[3] = f;
            float mag = eis->spectra[e][f].z_mag;
            float phase = eis->spectra[e][f].z_phase;
            if (isnan(mag)) mag = -1;
            if (isnan(phase)) phase = 0;
            memcpy(buf + 4, &mag, 4);
            memcpy(buf + 8, &phase, 4);
            buf[12] = 0; /* placeholder CRC */

            esp_ble_gatts_send_indicate(g_gatt_if, g_conn_id,
                                         g_handle_table[4], 13, buf, false);
        }
    }
    return ESP_OK;
}

esp_err_t ble_send_status(const char *status_msg)
{
    if (!g_connected || status_msg == NULL) return ESP_ERR_INVALID_STATE;

    uint8_t buf[33] = {0};
    buf[0] = BLE_MSG_STATUS;
    strncpy((char *)buf + 1, status_msg, 31);
    esp_ble_gatts_send_indicate(g_gatt_if, g_conn_id,
                                 g_handle_table[10], sizeof(buf), buf, false);
    return ESP_OK;
}

bool ble_is_connected(void)
{
    return g_connected;
}

esp_err_t ble_get_command(uint8_t *cmd, uint8_t *data, int *len)
{
    if (!g_cmd_ready) return ESP_ERR_NOT_FOUND;
    *cmd = g_cmd_opcode;
    if (data && len) {
        memcpy(data, g_cmd_buf, g_cmd_len);
        *len = g_cmd_len;
    }
    g_cmd_ready = false;
    return ESP_OK;
}