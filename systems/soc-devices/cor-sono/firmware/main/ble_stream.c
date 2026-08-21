/*
 * cor-sono / firmware / ble_stream.c
 * BLE 5.0 GATT service: audio stream + classification results + commands
 */
#include "main.h"
#include "ble_stream.h"
#include "esp_log.h"
#include "esp_bt.h"
#include "esp_bt_main.h"
#include "esp_gap_ble_api.h"
#include "esp_gatts_api.h"
#include "esp_bt_device.h"
#include <string.h>

static const char *TAG = "ble";

/* GATT UUIDs */
#define SVC_UUID       0x9201
#define CHR_AUDIO      0x9202
#define CHR_RESULT     0x9203
#define CHR_CMD        0x9204
#define CHR_INFO       0x9205

static uint16_t gatt_handle_table[5];
static uint16_t conn_id = 0xFFFF;
static bool connected = false;

/* BLE GATT event handler */
static void gatts_event_handler(esp_gatts_cb_event_t ev, esp_gatt_if_t gatts_if,
                                 esp_ble_gatts_cb_param_t *param)
{
    switch (ev) {
    case ESP_GATTS_REG_EVENT:
        /* Create service */
        break;
    case ESP_GATTS_CONNECT_EVENT:
        conn_id = param->connect.conn_id;
        connected = true;
        ESP_LOGI(TAG, "BLE connected");
        break;
    case ESP_GATTS_DISCONNECT_EVENT:
        connected = false;
        conn_id = 0xFFFF;
        esp_ble_gap_start_advertising(&adv_data);
        ESP_LOGI(TAG, "BLE disconnected, re-advertising");
        break;
    case ESP_GATTS_WRITE_EVENT:
        /* Handle command from client */
        if (param->write.handle == gatt_handle_table[3]) {
            uint8_t cmd = param->write.value[0];
            switch (cmd) {
            case 0x01: on_button_record(); break;  /* start/stop */
            case 0x02: on_button_mode();   break;  /* cycle mode */
            case 0x03: /* set volume */
                g_ctx.volume_db = param->write.value[1];
                if (g_ctx.volume_db > 30) g_ctx.volume_db = 30;
                break;
            }
        }
        break;
    default: break;
    }
}

static void gap_event_handler(esp_gap_ble_cb_event_t ev,
                               esp_ble_gap_cb_param_t *param)
{
    switch (ev) {
    case ESP_GAP_BLE_ADV_DATA_SET_COMPLETE_EVT:
        esp_ble_gap_start_advertising(&adv_data);
        break;
    default: break;
    }
}

void ble_stream_init(void)
{
    ESP_LOGI(TAG, "init BLE 5.0");

    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();

    esp_ble_gatts_register_callback(gatts_event_handler);
    esp_ble_gap_register_callback(gap_event_handler);
    esp_ble_gatts_app_register(0);

    /* Set device name */
    const char *name = "Cor Sono";
    esp_ble_gap_set_device_name(name);
}

void ble_send_audio_block(const int16_t *stereo, int n)
{
    if (!connected) return;
    /* Send 80-sample stereo block as 320 bytes via notify */
    esp_gatt_value_t val = {0};
    val.len = n * 2 * sizeof(int16_t);
    if (val.len > 500) val.len = 500;
    memcpy(val.value, stereo, val.len);
    esp_ble_gatts_send_indicate(0, conn_id, gatt_handle_table[1],
                                val.len, val.value, false);
}

void ble_send_result(int class_id, int confidence, int hr)
{
    if (!connected) return;
    uint8_t pkt[4] = { (uint8_t)class_id, (uint8_t)confidence,
                       (uint8_t)(hr & 0xFF), (uint8_t)(hr >> 8) };
    esp_ble_gatts_send_indicate(0, conn_id, gatt_handle_table[2],
                                sizeof(pkt), pkt, false);
}

bool ble_is_connected(void) { return connected; }