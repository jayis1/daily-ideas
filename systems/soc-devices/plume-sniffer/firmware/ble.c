/* ble.c — BLE GATT server (NimBLE)
 *
 * Services:
 *   0xPLU1 (Control)   — write characteristic to start/stop runs
 *   0xPLU2 (Chromatogram) — notify: batches of 20 float samples
 *   0xPLU3 (Results)   — notify: peak table entries
 */
#include <string.h>
#include "esp_log.h"
#include "nimble/nimble_port.h"
#include "nimble/ble.h"
#include "host/ble_hs.h"
#include "host/ble_gatt.h"

#include "sdkconfig.h"
#include "ble.h"
#include "library.h"

static const char *TAG = "ble";

static bool s_connected = false;
static uint16_t s_chr_chrom_handle = 0;
static uint16_t s_chr_result_handle = 0;
static uint16_t s_chr_ctrl_handle = 0;
static uint16_t s_conn_handle = BLE_HS_CONN_HANDLE_NONE;

/* GATT service UUIDs (128-bit, custom) */
static const ble_uuid128_t s_svc_uuid =
    BLE_UUID128_INIT(0xPL,0xPL,0xPL,0xPL,0xPL,0xPL,0xPL,0xPL,
                     0xPL,0xPL,0xPL,0xPL,0xPL,0xPL,0xPL,0xPL);

/* For brevity, use 16-bit UUIDs */
#define UUID_SVC_CTRL    0x1840
#define UUID_CHR_CTRL    0x1841
#define UUID_CHR_CHROM   0x1842
#define UUID_CHR_RESULT  0x1843

static int gatt_ctrl_access(uint16_t conn, uint16_t attr,
                            struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t cmd[16] = {0};
        int len = os_mbuf_len(ctxt->om);
        if (len > 16) len = 16;
        os_mbuf_copydata(ctxt->om, 0, len, cmd);
        ESP_LOGI(TAG, "Control write: cmd=%d", cmd[0]);
        /* 0x01 = start run, 0x02 = stop, 0x03 = set method (cmd[1]) */
        /* Forward to UI queue — handled in ui.c */
    }
    return 0;
}

static const struct ble_gatt_svc_def s_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(UUID_SVC_CTRL),
        .characteristics = (struct ble_gatt_chr_def[]) {
            {
                .uuid = BLE_UUID16_DECLARE(UUID_CHR_CTRL),
                .access_cb = gatt_ctrl_access,
                .flags = BLE_GATT_CHR_F_WRITE,
            },
            {
                .uuid = BLE_UUID16_DECLARE(UUID_CHR_CHROM),
                .access_cb = gatt_ctrl_access,  /* read returns 0 */
                .flags = BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &s_chr_chrom_handle,
            },
            {
                .uuid = BLE_UUID16_DECLARE(UUID_CHR_RESULT),
                .access_cb = gatt_ctrl_access,
                .flags = BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &s_chr_result_handle,
            },
            { 0 }
        },
    },
    { 0 }
};

static int gap_event(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0) {
            s_conn_handle = event->connect.conn_handle;
            s_connected = true;
            ESP_LOGI(TAG, "BLE connected: handle=%d", s_conn_handle);
        } else {
            s_connected = false;
        }
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        s_connected = false;
        s_conn_handle = BLE_HS_CONN_HANDLE_NONE;
        ESP_LOGI(TAG, "BLE disconnected");
        break;
    default:
        break;
    }
    return 0;
}

static void ble_advertise(void)
{
    struct ble_hs_adv_fields fields = {0};
    fields.name = (const uint8_t *)"Plume Sniffer";
    fields.name_len = 12;
    fields.name_is_complete = 1;
    ble_gap_adv_set_fields(&fields);

    struct ble_gap_adv_params adv = {0};
    adv.conn_mode = BLE_GAP_CONN_MODE_UND;
    adv.disc_mode = BLE_GAP_DISC_MODE_GEN;
    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &adv, gap_event, NULL);
}

static void ble_sync_cb(void)
{
    ble_advertise();
}

static void ble_host_task(void *p)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
}

void ble_init(void)
{
    ESP_LOGI(TAG, "Initializing BLE (NimBLE)");
    esp_err_t ret = nimble_port_init();
    if (ret != ESP_OK) { ESP_LOGE(TAG, "nimble init: %s", esp_err_to_name(ret)); return; }

    ble_svc_gap_device_name_set("Plume Sniffer");
    ble_gatts_count_cfg(s_svcs);
    ble_gatts_add_svcs(s_svcs);
    ble_hs_sync_init_register(ble_sync_cb);

    nimble_port_freertos_init(ble_host_task);
}

void ble_send_chromatogram(const float *data, int n)
{
    if (!s_connected) return;
    /* Send up to 20 floats (80 bytes) per notification */
    uint8_t buf[80];
    int send = n < 20 ? n : 20;
    memcpy(buf, data, send * sizeof(float));
    struct os_mbuf *om = ble_hs_mbuf_from_flat(buf, send * sizeof(float));
    if (om) ble_gattc_notify(s_conn_handle, s_chr_chrom_handle, om);
}

void ble_send_results(const identification_t *ids, int n)
{
    if (!s_connected) return;
    for (int i = 0; i < n; i++) {
        struct {
            float tR;
            float RI;
            float conc;
            int16_t idx;
            int16_t pad;
        } __attribute__((packed)) pkt;
        pkt.tR = ids[i].retention_s;
        pkt.RI = ids[i].retention_index;
        pkt.conc = ids[i].est_conc_ppm;
        pkt.idx = ids[i].n_matches > 0 ? ids[i].matches[0].index : -1;
        pkt.pad = 0;
        struct os_mbuf *om = ble_hs_mbuf_from_flat(&pkt, sizeof(pkt));
        if (om) ble_gattc_notify(s_conn_handle, s_chr_result_handle, om);
        vTaskDelay(pdMS_TO_TICKS(10));  /* throttle */
    }
}

bool ble_is_connected(void) { return s_connected; }