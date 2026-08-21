/*
 * ble_hid.c — BLE HID Keyboard service for Scribe Nib
 *
 * Appears as a standard Bluetooth keyboard to any host.
 * Sends recognized characters as keystrokes.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "ble_hid.h"
#include <string.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_bt_device.h"
#include "esp_hidd.h"
#include "esp_hid_common.h"

static const char *TAG = "ble_hid";

/* HID report map: standard US keyboard */
static const uint8_t hid_report_map[] = {
    0x05, 0x01,  /* Usage Page (Generic Desktop Ctrls) */
    0x09, 0x06,  /* Usage (Keyboard) */
    0xA1, 0x01,  /* Collection (Application) */
    0x85, 0x01,  /*   Report ID (1) */
    0x05, 0x07,  /*   Usage Page (Kbrd/Keypad) */
    0x19, 0xE0,  /*   Usage Minimum (0xE0) */
    0x29, 0xE7,  /*   Usage Maximum (0xE7) */
    0x15, 0x00,  /*   Logical Minimum (0) */
    0x25, 0x01,  /*   Logical Maximum (1) */
    0x75, 0x01,  /*   Report Size (1) */
    0x95, 0x08,  /*   Report Count (8) */
    0x81, 0x02,  /*   Input (Data,Var,Abs) */
    0x95, 0x01,  /*   Report Count (1) */
    0x75, 0x08,  /*   Report Size (8) */
    0x81, 0x01,  /*   Input (Const) — reserved byte */
    0x95, 0x06,  /*   Report Count (6) */
    0x75, 0x08,  /*   Report Size (8) */
    0x15, 0x00,  /*   Logical Minimum (0) */
    0x25, 0x65,  /*   Logical Maximum (101) */
    0x05, 0x07,  /*   Usage Page (Kbrd/Keypad) */
    0x19, 0x00,  /*   Usage Minimum (0) */
    0x29, 0x65,  /*   Usage Maximum (101) */
    0x81, 0x00,  /*   Input (Data,Arr,Abs) */
    0xC0,        /* End Collection */
};

/* BLE connection state */
static bool is_connected = false;
static uint16_t conn_id = 0;
static esp_hidd_dev_t *hid_dev = NULL;

/* ASCII to HID keycode lookup table */
static uint8_t ascii_to_hid(char c)
{
    if (c >= 'a' && c <= 'z') return (uint8_t)(c - 'a' + 0x04);
    if (c >= 'A' && c <= 'Z') return (uint8_t)(c - 'A' + 0x04);
    if (c >= '0' && c <= '9') {
        if (c == '0') return 0x27;
        return (uint8_t)(c - '1' + 0x1E);
    }
    switch (c) {
        case ' ':  return 0x2C;
        case '\n': return 0x28;  /* Enter */
        case '\b': return 0x2A;  /* Backspace */
        case '\t': return 0x2B;  /* Tab */
        case '.':  return 0x37;
        case ',':  return 0x36;
        case '!':  return 0x1E;  /* with shift */
        default:   return 0x00;
    }
}

static bool needs_shift(char c)
{
    if (c >= 'A' && c <= 'Z') return true;
    if (c == '!' || c == '@' || c == '#') return true;
    return false;
}

/* ---- GAP event handler ---- */

static void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param)
{
    switch (event) {
        case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
            ESP_LOGD(TAG, "Adv data set complete");
            break;
        case ESP_GAP_BLE_SCAN_PARAM_SET_COMPLETE_EVT:
            break;
        case ESP_GAP_BLE_UPDATE_CONN_PARAMS_EVT:
            ESP_LOGI(TAG, "Connection params updated: status=%d", param->update_conn_params.status);
            break;
        default:
            break;
    }
}

/* ---- HIDD event handler ---- */

static void hidd_event_handler(esp_hidd_cb_event_t event, esp_hidd_cb_param_t *param)
{
    switch (event) {
        case ESP_HIDD_INIT_EVT:
            ESP_LOGI(TAG, "HIDD init complete");
            break;
        case ESP_HIDD_DEINIT_EVT:
            ESP_LOGI(TAG, "HIDD deinit");
            break;
        case ESP_HIDD_REGISTER_APP_EVT:
            ESP_LOGI(TAG, "HIDD app registered: status=%d", param->register_app.status);
            break;
        case ESP_HIDD_OPEN_EVT:
            ESP_LOGI(TAG, "HIDD connection opened: conn_id=%d", param->open.conn_id);
            is_connected = true;
            conn_id = param->open.conn_id;
            break;
        case ESP_HIDD_CLOSE_EVT:
            ESP_LOGI(TAG, "HIDD connection closed");
            is_connected = false;
            break;
        case ESP_HIDD_SEND_REPORT_EVT:
            break;
        case ESP_HIDD_REPORT_RSP_EVT:
            break;
        case ESP_HIDD_BLE_DISCONNECT_EVT:
            ESP_LOGI(TAG, "BLE disconnected");
            is_connected = false;
            /* Restart advertising */
            if (hid_dev) {
                esp_ble_hid_start_advertising(hid_dev);
            }
            break;
        default:
            break;
    }
}

/* ---- Public API ---- */

esp_err_t ble_hid_init(const char *device_name)
{
    esp_err_t ret;

    /* Initialize Bluedroid */
    ESP_ERROR_CHECK(esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT));

    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_bt_controller_init(&bt_cfg));
    ESP_ERROR_CHECK(esp_bt_controller_enable(ESP_BT_MODE_BLE));
    ESP_ERROR_CHECK(esp_bluedroid_init());
    ESP_ERROR_CHECK(esp_bluedroid_enable());

    /* Set device name */
    ESP_ERROR_CHECK(esp_ble_dev_set_device_name(device_name));

    /* Register GAP callback */
    ESP_ERROR_CHECK(esp_ble_gap_register_callback(gap_event_handler));

    /* Initialize HIDD */
    esp_hidd_config_t hidd_cfg = {
        .hid_mode = ESP_HID_MODE_BLE,
    };
    ESP_ERROR_CHECK(esp_hidd_init(&hidd_cfg, hidd_event_handler, &hid_dev));

    /* Register HID report map */
    esp_hid_report_map_t map = {
        .data = hid_report_map,
        .len = sizeof(hid_report_map),
    };
    ESP_ERROR_CHECK(esp_hidd_register_map(hid_dev, &map));

    /* Set security: Just Works pairing */
    esp_ble_auth_req_t auth_req = ESP_LE_AUTH_NO_BOND;
    ESP_ERROR_CHECK(esp_ble_gap_set_security_param(ESP_BLE_SM_AUTHEN_REQ_MODE, &auth_req, sizeof(auth_req)));

    /* Start advertising */
    ESP_ERROR_CHECK(esp_ble_hid_start_advertising(hid_dev));

    ESP_LOGI(TAG, "BLE HID keyboard initialized as '%s'", device_name);
    return ESP_OK;
}

esp_err_t ble_hid_send_key(char c)
{
    if (!hid_dev || !is_connected) {
        ESP_LOGD(TAG, "Not connected, queuing key '%c'", c);
        return ESP_ERR_INVALID_STATE;
    }

    uint8_t report[8] = {0};  /* modifier + reserved + 6 keycodes */
    uint8_t keycode = ascii_to_hid(c);

    if (needs_shift(c)) {
        report[0] = 0x02;  /* Left Shift modifier */
    }
    report[2] = keycode;  /* First keycode position */

    /* Send key down */
    esp_hidd_send_report(hid_dev, ESP_HIDD_REPORT_TYPE_INPUT, 1, report, 8);

    /* Send key up (all zeros) after 15ms */
    uint8_t release[8] = {0};
    vTaskDelay(pdMS_TO_TICKS(15));
    esp_hidd_send_report(hid_dev, ESP_HIDD_REPORT_TYPE_INPUT, 1, release, 8);

    return ESP_OK;
}

bool ble_hid_is_connected(void)
{
    return is_connected;
}