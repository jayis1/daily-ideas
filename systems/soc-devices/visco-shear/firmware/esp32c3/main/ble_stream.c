/*
 * visco-shear / firmware / esp32c3 / main / ble_stream.c
 * BLE GATT server for Visco Shear data streaming
 *
 * Service UUID: 0xA101
 * Characteristics:
 *   0xA102 (Notify) — Torque data stream
 *   0xA103 (Read/Notify) — Measurement result
 *   0xA104 (Write) — Command
 *   0xA105 (Read) — Device info
 *
 * MIT License.
 */
#include <string.h>
#include "esp_log.h"
#include "host/ble_hs.h"
#include "host/ble_uuid.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

#include "ble_stream.h"

static const char *TAG = "ble_stream";

/* Custom service + characteristic UUIDs (16-bit) */
#define VS_SERVICE_UUID       0xA101
#define VS_CHAR_TORQUE_UUID   0xA102
#define VS_CHAR_RESULT_UUID   0xA103
#define VS_CHAR_CMD_UUID      0xA104
#define VS_CHAR_INFO_UUID     0xA105

static uint8_t torque_data[24];
static uint8_t result_data[64];
static uint8_t info_data[48];
static uint16_t conn_handle = BLE_HS_CONN_HANDLE_NONE;
static uint16_t torque_val_handle;
static uint16_t result_val_handle;

static int vs_access_torque(uint16_t conn, uint16_t attr, uint16_t op,
                            struct ble_gatt_access_ctxt *ctxt, void *arg);
static int vs_access_result(uint16_t conn, uint16_t attr, uint16_t op,
                            struct ble_gatt_access_ctxt *ctxt, void *arg);
static int vs_access_cmd(uint16_t conn, uint16_t attr, uint16_t op,
                         struct ble_gatt_access_ctxt *ctxt, void *arg);
static int vs_access_info(uint16_t conn, uint16_t attr, uint16_t op,
                          struct ble_gatt_access_ctxt *ctxt, void *arg);

static const struct ble_gatt_svc_def vs_gatt_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(VS_SERVICE_UUID),
        .characteristics = (struct ble_gatt_chr_def[]) {
            {
                .uuid = BLE_UUID16_DECLARE(VS_CHAR_TORQUE_UUID),
                .access_cb = vs_access_torque,
                .val_handle = &torque_val_handle,
                .flags = BLE_GATT_CHR_F_NOTIFY,
            },
            {
                .uuid = BLE_UUID16_DECLARE(VS_CHAR_RESULT_UUID),
                .access_cb = vs_access_result,
                .val_handle = &result_val_handle,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
            },
            {
                .uuid = BLE_UUID16_DECLARE(VS_CHAR_CMD_UUID),
                .access_cb = vs_access_cmd,
                .flags = BLE_GATT_CHR_F_WRITE,
            },
            {
                .uuid = BLE_UUID16_DECLARE(VS_CHAR_INFO_UUID),
                .access_cb = vs_access_info,
                .flags = BLE_GATT_CHR_F_READ,
            },
            { 0 }  /* End of characteristics */
        }
    },
    { 0 }  /* End of services */
};

static int vs_access_torque(uint16_t conn, uint16_t attr, uint16_t op,
                            struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    /* Notify-only characteristic; read returns current buffer */
    if (op == BLE_GATT_ACCESS_OP_READ_CHR) {
        return os_mbuf_append(ctxt->om, torque_data, sizeof(torque_data));
    }
    return 0;
}

static int vs_access_result(uint16_t conn, uint16_t attr, uint16_t op,
                            struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    if (op == BLE_GATT_ACCESS_OP_READ_CHR) {
        return os_mbuf_append(ctxt->om, result_data, sizeof(result_data));
    }
    return 0;
}

static int vs_access_cmd(uint16_t conn, uint16_t attr, uint16_t op,
                         struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    if (op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t buf[64];
        int len = OS_MBUF_PKTLEN(ctxt->om);
        if (len > sizeof(buf)) len = sizeof(buf);
        ble_hs_mbuf_from_flat(ctxt->om, buf, len);
        /* Forward command to RP2040 via UART */
        ESP_LOGI(TAG, "Received BLE command: 0x%02x, forwarding to RP2040", buf[0]);
        /* uart_write_bytes(UART_NUM_1, frame, frame_len); */
    }
    return 0;
}

static int vs_access_info(uint16_t conn, uint16_t attr, uint16_t op,
                          struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    if (op == BLE_GATT_ACCESS_OP_READ_CHR) {
        return os_mbuf_append(ctxt->om, info_data, sizeof(info_data));
    }
    return 0;
}

static int vs_gap_event(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0) {
            conn_handle = event->connect.conn_handle;
            ESP_LOGI(TAG, "BLE connected, handle=%d", conn_handle);
        } else {
            conn_handle = BLE_HS_CONN_HANDLE_NONE;
            ble_advertising_start();  /* Restart advertising */
        }
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        conn_handle = BLE_HS_CONN_HANDLE_NONE;
        ESP_LOGI(TAG, "BLE disconnected, restarting advertising");
        ble_advertising_start();
        break;
    }
    return 0;
}

void ble_stream_init(void)
{
    ble_svc_gap_init();
    ble_svc_gatt_init();

    int rc = ble_gatts_count_cfg(vs_gatt_svcs);
    ESP_ERROR_CHECK(rc == 0 ? ESP_OK : ESP_FAIL);

    rc = ble_gatts_add_svcs(vs_gatt_svcs);
    ESP_ERROR_CHECK(rc == 0 ? ESP_OK : ESP_FAIL);

    /* Set device name */
    ble_svc_gap_device_name_set("Visco Shear");

    /* Start advertising */
    struct ble_hs_adv_fields fields = {0};
    fields.name = (uint8_t *)"Visco Shear";
    fields.name_len = strlen("Visco Shear");
    fields.name_is_complete = 1;
    ble_gap_adv_set_fields(&fields);

    ble_advertising_start();
}

void ble_stream_process_frame(const uint8_t *data, int len)
{
    /* Parse RP2040 frame: [0xAA][0x55][cmd][len_lo][len_hi][payload][crc] */
    if (len < 6) return;
    if (data[0] != 0xAA || data[1] != 0x55) return;

    uint8_t cmd = data[2];
    int plen = data[3] | (data[4] << 8);

    if (cmd == 0x10 && plen == 6) {
        /* Torque sample → notify */
        memcpy(torque_data, &data[5], 6);
        if (conn_handle != BLE_HS_CONN_HANDLE_NONE) {
            ble_gattc_notify(conn_handle, torque_val_handle);
        }
    } else if (cmd == 0x11) {
        /* Result → store + notify */
        int copy_len = plen < (int)sizeof(result_data) ? plen : (int)sizeof(result_data);
        memcpy(result_data, &data[5], copy_len);
        if (conn_handle != BLE_HS_CONN_HANDLE_NONE) {
            ble_gattc_notify(conn_handle, result_val_handle);
        }
        ESP_LOGI(TAG, "Result received from RP2040 (model=%d)", result_data[0]);
    } else if (cmd == 0x12) {
        /* Info → store */
        int copy_len = plen < (int)sizeof(info_data) ? plen : (int)sizeof(info_data);
        memcpy(info_data, &data[5], copy_len);
    }
}