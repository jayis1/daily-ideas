/*
 * kappa-pin / firmware / main / ble_stream.c
 * BLE GATT peripheral for live data streaming + commands (NimBLE)
 *
 * MIT License.
 */
#include "ble_stream.h"
#include "esp_log.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *TAG = "ble";

static bool connected = false;
static uint16_t conn_handle = BLE_HS_CONN_HANDLE_NONE;
static bool notify_enabled = false;
static ble_cmd_callback_t cmd_callback = NULL;

/* GATT handles */
static uint16_t handle_data;
static uint16_t handle_result;
static uint16_t handle_cmd;

/* ---- GATT access callbacks ---- */

static int data_chr_access(uint16_t conn, uint16_t access, void *arg)
{
    struct ble_gatt_access_ctxt *ctxt = arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_DUMMY) {
        /* CCCD write — notifications enabled */
        notify_enabled = true;
    }
    return 0;
}

static int result_chr_access(uint16_t conn, uint16_t access, void *arg)
{
    /* Read access handled by storing result in context */
    return 0;
}

static int cmd_chr_access(uint16_t conn, uint16_t access, void *arg)
{
    struct ble_gatt_access_ctxt *ctxt = arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t buf[32];
        int len = OS_MBUF_PKTLEN(ctxt->om);
        if (len > 32) len = 32;
        ble_hs_mbuf_from_flat(ctxt->om, buf, len);
        if (cmd_callback && len >= 1) {
            cmd_callback(buf[0], buf + 1, len - 1);
        }
    }
    return 0;
}

/* GATT service definition */
static const struct ble_gatt_svc_def kappa_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(UUID_KAPPA_SERVICE),
        .characteristics = (struct ble_gatt_chr_def[]) {
            {
                .uuid = BLE_UUID16_DECLARE(UUID_KAPPA_DATA),
                .access_cb = data_chr_access,
                .flags = BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &handle_data,
            },
            {
                .uuid = BLE_UUID16_DECLARE(UUID_KAPPA_RESULT),
                .access_cb = result_chr_access,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &handle_result,
            },
            {
                .uuid = BLE_UUID16_DECLARE(UUID_KAPPA_CMD),
                .access_cb = cmd_chr_access,
                .flags = BLE_GATT_CHR_F_WRITE,
                .val_handle = &handle_cmd,
            },
            { 0 }
        },
    },
    { 0 }
};

static int kappa_gap_event(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0) {
            conn_handle = event->connect.conn_handle;
            connected = true;
            ESP_LOGI(TAG, "BLE connected: handle=%d", conn_handle);
        } else {
            connected = false;
            notify_enabled = false;
        }
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        connected = false;
        notify_enabled = false;
        conn_handle = BLE_HS_CONN_HANDLE_NONE;
        ESP_LOGI(TAG, "BLE disconnected");
        break;
    case BLE_GAP_EVENT_SUBSCRIBE:
        if (event->subscribe.attr_handle == handle_data) {
            notify_enabled = event->subscribe.cur_notify;
        }
        break;
    default:
        break;
    }
    return 0;
}

static void kappa_advertise(void)
{
    struct ble_hs_adv_fields fields = {0};
    const char *name = "KappaPin";
    fields.name = (uint8_t *)name;
    fields.name_len = strlen(name);
    fields.name_is_complete = 1;
    ble_gap_adv_set_fields(&fields);

    struct ble_gap_adv_params adv_params = {0};
    adv_params.conn_mode = BLE_GAP_CONN_MODE_UND;
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;
    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER,
                      &adv_params, kappa_gap_event, NULL);
}

static void kappa_on_sync(void)
{
    kappa_advertise();
}

static void ble_host_task(void *param)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
    vTaskDelete(NULL);
}

void ble_stream_init(void)
{
    ESP_ERROR_CHECK(nimble_port_init());
    ble_svc_gatt_init();
    ble_svc_gap_init();

    int rc = ble_gatts_count_cfg(kappa_svcs);
    assert(rc == 0);
    rc = ble_gatts_add_svcs(kappa_svcs);
    assert(rc == 0);

    ble_hs_cfg.sync_cb = kappa_on_sync;
    ble_svc_gap_device_name_set("KappaPin");

    nimble_port_freertos_init(ble_host_task);
    ESP_LOGI(TAG, "BLE initialized");
}

void ble_stream_send_sample(const meas_sample_t *s)
{
    if (!connected || !notify_enabled) return;

    /* Pack: ts_u16 (ms / 10) + dT_x4_s16 + Q_x4_s16 = 6 bytes */
    uint8_t buf[6];
    uint16_t ts = (uint16_t)(s->t_s * 100.0f);  /* centiseconds */
    int16_t dt = (int16_t)(s->dt_mk * 4.0f);    /* mK × 4 for resolution */
    int16_t q = (int16_t)(s->q_w * 1000.0f);    /* mW */
    memcpy(buf, &ts, 2);
    memcpy(buf + 2, &dt, 2);
    memcpy(buf + 4, &q, 2);

    struct os_mbuf *om = ble_hs_mbuf_from_flat(buf, 6);
    if (om) {
        ble_gattc_notify(conn_handle, handle_data, om);
    }
}

void ble_stream_send_result(const meas_result_t *r)
{
    if (!connected) return;

    /* Pack result: 4 floats + 1 byte = 17 bytes */
    uint8_t buf[17];
    memcpy(buf, &r->lambda, 4);
    memcpy(buf + 4, &r->alpha, 4);
    memcpy(buf + 8, &r->rho_cp, 4);
    memcpy(buf + 12, &r->effusivity, 4);
    buf[16] = (uint8_t)r->final_state;

    struct os_mbuf *om = ble_hs_mbuf_from_flat(buf, 17);
    if (om) {
        ble_gattc_notify(conn_handle, handle_result, om);
    }
}

bool ble_stream_is_connected(void) { return connected; }

void ble_stream_set_cmd_callback(ble_cmd_callback_t cb) { cmd_callback = cb; }