/*
 * ble_service.c — BLE GATT server for Phyto Pulse
 * Provides waveform stream, event notifications, status, and command interface.
 */

#include "ble_service.h"
#include "esp_log.h"
#include "esp_gatts_api.h"
#include "esp_gap_ble_api.h"
#include "esp_bt_main.h"

static const char *TAG = "ble_svc";

#define PROFILE_NUM 1
#define PROFILE_APP_IDX 0
#define CHAR_NUM 4

static uint16_t g_gatts_if = ESP_GATT_IF_NONE;
static uint16_t g_conn_id = 0;
static bool g_connected = false;
static uint16_t g_char_handles[CHAR_NUM];

/* Sample queue for notification task */
#define SAMPLE_QUEUE_LEN 128
typedef struct {
    float voltage_mv;
    uint32_t timestamp_ms;
} sample_t;
static QueueHandle_t g_sample_queue;

/* Service UUID */
static esp_bt_uuid_t svc_uuid = {
    .len = ESP_UUID_LEN_16,
    .uuid = { .uuid16 = 0x180C }
};

static esp_gatts_attr_db_t gatt_db[CHAR_NUM + 2] = {0};

void ble_service_init(void)
{
    g_sample_queue = xQueueCreate(SAMPLE_QUEUE_LEN, sizeof(sample_t));

    esp_bt_controller_config_t bt_cfg = BT_CONTROLLER_INIT_CONFIG_DEFAULT();
    esp_bt_controller_init(&bt_cfg);
    esp_bt_controller_enable(ESP_BT_MODE_BLE);
    esp_bluedroid_init();
    esp_bluedroid_enable();

    /* In a full implementation, register GATT service with attributes:
     *   - Primary Service (0x180C)
     *   - Characteristic: Waveform (0xFF01, notify)
     *   - Characteristic: Event (0xFF02, notify)
     *   - Characteristic: Status (0xFF03, read+notify)
     *   - Characteristic: Command (0xFF04, write)
     */
    ESP_LOGI(TAG, "BLE GATT service initialized (simplified)");
}

void ble_notify_task(void *arg)
{
    sample_t s;
    while (1) {
        if (g_connected && g_sample_queue) {
            if (xQueueReceive(g_sample_queue, &s, pdMS_TO_TICKS(100))) {
                /* Pack: [ts_lo][ts_hi][v_lo][v_hi] (4+2 bytes) */
                uint8_t pkt[6];
                pkt[0] = s.timestamp_ms & 0xFF;
                pkt[1] = (s.timestamp_ms >> 8) & 0xFF;
                pkt[2] = (s.timestamp_ms >> 16) & 0xFF;
                pkt[3] = (s.timestamp_ms >> 24) & 0xFF;
                int16_t v_scaled = (int16_t)(s.voltage_mv * 100);
                pkt[4] = v_scaled & 0xFF;
                pkt[5] = (v_scaled >> 8) & 0xFF;

                esp_ble_gatts_send_indicate(g_gatts_if, g_conn_id,
                    g_char_handles[0], sizeof(pkt), pkt, false);
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}

void ble_send_sample(float voltage_mv, uint32_t timestamp_ms)
{
    if (!g_sample_queue) return;
    sample_t s = { .voltage_mv = voltage_mv, .timestamp_ms = timestamp_ms };
    xQueueSendToBack(g_sample_queue, &s, 0);
}

void ble_send_event(const char *json, int len)
{
    if (g_connected) {
        esp_ble_gatts_send_indicate(g_gatts_if, g_conn_id,
            g_char_handles[1], len, (uint8_t *)json, false);
    }
}

void ble_send_command_response(const char *response)
{
    if (g_connected) {
        esp_ble_gatts_send_indicate(g_gatts_if, g_conn_id,
            g_char_handles[1], strlen(response), (uint8_t *)response, false);
    }
}

void ble_service_send_status(void)
{
    /* Periodic status broadcast */
    if (g_connected) {
        const char *status = "{\"t\":\"heartbeat\"}";
        esp_ble_gatts_send_indicate(g_gatts_if, g_conn_id,
            g_char_handles[2], strlen(status), (uint8_t *)status, false);
    }
}