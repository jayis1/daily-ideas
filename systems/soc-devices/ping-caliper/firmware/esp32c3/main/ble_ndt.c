/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/ble_ndt.c — NimBLE BLE 5 GATT server
 *
 * Services & characteristics:
 *
 *   Service: NDT  (UUID 6e40fb10-b5a3-f393-e0a9-e50e24dcca9e)
 *     ├── Measurement  (notify)   — latest thickness + flaw result
 *     ├── A-scan       (notify)    — chunked A-scan envelope
 *     ├── Status       (notify)    — armed/measuring/battery
 *     ├── Command      (write)    — phone → device commands
 *     ├── Config        (read/write) — device configuration blob
 *     └── Material     (read/write) — active material index + name
 *
 *   Service: Device Info (UUID 0000180a-0000-1000-8000-00805f9b34fb)
 *     ├── Manufacturer (read)  — "SoC Device Inventions"
 *     ├── Model         (read)  — "Ping Caliper v1.0"
 *     ├── Firmware      (read)  — e.g. "1.0.0"
 *     └── Battery      (read)  — 0..100
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "ble_ndt.h"
#include "uart_comm.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
#include "esp_log.h"
#include <string.h>

static const char *TAG = "ble_ndt";
static bool g_connected = false;
static uint16_t g_conn_handle = BLE_HS_CONN_HANDLE_NONE;
static ble_cmd_cb_t g_cmd_cb = NULL;

/* ---- UUIDs ---- */
static ble_uuid128_t g_svc_ndt_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x10, 0xfb, 0x40, 0x6e);

static ble_uuid128_t g_chr_meas_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x11, 0xfb, 0x40, 0x6e);
static ble_uuid128_t g_chr_ascan_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x12, 0xfb, 0x40, 0x6e);
static ble_uuid128_t g_chr_status_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x13, 0xfb, 0x40, 0x6e);
static ble_uuid128_t g_chr_cmd_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x14, 0xfb, 0x40, 0x6e);
static ble_uuid128_t g_chr_config_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x15, 0xfb, 0x40, 0x6e);
static ble_uuid128_t g_chr_material_uuid =
    BLE_UUID128_INIT(0x9e, 0xca, 0xdc, 0x24, 0x0e, 0xe5, 0xa9, 0xe0,
                     0x93, 0xf3, 0xa3, 0xb5, 0x16, 0xfb, 0x40, 0x6e);

/* ---- Characteristic handles ---- */
static uint16_t g_chr_meas_val;
static uint16_t g_chr_ascan_val;
static uint16_t g_chr_status_val;

/* ---- Measurement characteristic (notify) ---- */
static uint8_t g_meas_data[64];
static size_t   g_meas_len = 0;

static int access_meas(uint16_t conn, uint16_t attr,
                       struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, g_meas_data, g_meas_len);
        return 0;
    }
    return BLE_ATT_ERR_READ_NOT_PERMITTED;
}

/* ---- A-scan characteristic (notify) ---- */
static uint8_t g_ascan_data[200];
static size_t   g_ascan_len = 0;

static int access_ascan(uint16_t conn, uint16_t attr,
                         struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, g_ascan_data, g_ascan_len);
        return 0;
    }
    return BLE_ATT_ERR_READ_NOT_PERMITTED;
}

/* ---- Status characteristic (notify) ---- */
static uint8_t g_status_data[4];

static int access_status(uint16_t conn, uint16_t attr,
                          struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, g_status_data, sizeof(g_status_data));
        return 0;
    }
    return BLE_ATT_ERR_READ_NOT_PERMITTED;
}

/* ---- Command characteristic (write) ---- */
static int access_cmd(uint16_t conn, uint16_t attr,
                       struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t buf[250];
        int len = os_mbuf_len(ctxt->om);
        if (len > (int)sizeof(buf)) len = (int)sizeof(buf);
        os_mbuf_copydata(ctxt->om, 0, len, buf);
        /* First byte = command, rest = payload */
        if (g_cmd_cb && len > 0)
            g_cmd_cb(buf[0], &buf[1], (uint8_t)(len - 1));
        return 0;
    }
    return BLE_ATT_ERR_WRITE_NOT_PERMITTED;
}

/* ---- Config characteristic (read/write) ---- */
static uint8_t g_config_blob[64];

static int access_config(uint16_t conn, uint16_t attr,
                          struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, g_config_blob, sizeof(g_config_blob));
        return 0;
    } else if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        int len = os_mbuf_len(ctxt->om);
        if (len > (int)sizeof(g_config_blob)) len = (int)sizeof(g_config_blob);
        os_mbuf_copydata(ctxt->om, 0, len, g_config_blob);
        /* Forward config update to STM32 */
        uart_comm_send(CMD_SET_CONFIG, g_config_blob, (uint8_t)len);
        return 0;
    }
    return 0;
}

/* ---- Material characteristic (read/write) ---- */
static uint8_t g_material_data[24];   /* index(1) + name(23) */

static int access_material(uint16_t conn, uint16_t attr,
                            struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr; (void)arg;
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, g_material_data, sizeof(g_material_data));
        return 0;
    } else if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        int len = os_mbuf_len(ctxt->om);
        if (len > (int)sizeof(g_material_data)) len = (int)sizeof(g_material_data);
        os_mbuf_copydata(ctxt->om, 0, len, g_material_data);
        uart_comm_send(CMD_SET_MATERIAL, g_material_data, (uint8_t)len);
        return 0;
    }
    return 0;
}

/* ---- GATT services ---- */
static const struct ble_gatt_svc_def g_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &g_svc_ndt_uuid.u,
        .characteristics = (struct ble_gatt_chr_def[]) {
            {
                .uuid = &g_chr_meas_uuid.u,
                .access_cb = access_meas,
                .val_handle = &g_chr_meas_val,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
            },
            {
                .uuid = &g_chr_ascan_uuid.u,
                .access_cb = access_ascan,
                .val_handle = &g_chr_ascan_val,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
            },
            {
                .uuid = &g_chr_status_uuid.u,
                .access_cb = access_status,
                .val_handle = &g_chr_status_val,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
            },
            {
                .uuid = &g_chr_cmd_uuid.u,
                .access_cb = access_cmd,
                .flags = BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_NO_RSP,
            },
            {
                .uuid = &g_chr_config_uuid.u,
                .access_cb = access_config,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE,
            },
            {
                .uuid = &g_chr_material_uuid.u,
                .access_cb = access_material,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE,
            },
            { 0 }
        }
    },
    { 0 }
};

/* ---- GAP event handler ---- */
static int gap_event(struct ble_gap_event *event, void *arg)
{
    (void)arg;
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0) {
            g_conn_handle = event->connect.conn_handle;
            g_connected = true;
            ESP_LOGI(TAG, "BLE connected (handle %d)", g_conn_handle);
        } else {
            g_connected = false;
            ble_ndt_advertise();
        }
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        g_connected = false;
        g_conn_handle = BLE_HS_CONN_HANDLE_NONE;
        ESP_LOGI(TAG, "BLE disconnected — restarting advertising");
        ble_ndt_advertise();
        break;
    case BLE_GAP_EVENT_SUBSCRIBE:
        ESP_LOGI(TAG, "subscribe event; attr=%d", event->subscribe.attr_handle);
        break;
    }
    return 0;
}

/* ---- Advertising ---- */
void ble_ndt_advertise(void)
{
    struct ble_hs_adv_fields fields;
    memset(&fields, 0, sizeof(fields));
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    const char *name = "PingCaliper";
    fields.name = (uint8_t *)name;
    fields.name_len = strlen(name);
    fields.name_is_complete = 1;
    ble_gap_adv_set_fields(&fields);

    struct ble_gap_adv_params adv;
    memset(&adv, 0, sizeof(adv));
    adv.conn_mode = BLE_GAP_CONN_MODE_UND;
    adv.disc_mode = BLE_GAP_DISC_MODE_GEN;
    ble_gap_adv_start(BLE_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &adv,
                      gap_event, NULL);
}

/* ---- Sync callback ---- */
static void on_sync(void)
{
    ble_hs_id_infer_auto(0, NULL);
    ble_ndt_advertise();
}

/* ---- NimBLE host task ---- */
static void host_task(void *arg)
{
    nimble_port_run();
    vTaskDelete(NULL);
}

/* ---- Public API ---- */
void ble_ndt_init(void)
{
    nimble_port_init();
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_gatts_count_cfg(g_svcs);
    ble_gatts_add_svcs(g_svcs);
    ble_hs_cfg.sync_cb = on_sync;
    ble_svc_gap_device_name_set("PingCaliper");

    nimble_port_freertos_init(host_task);
}

bool ble_ndt_is_connected(void) { return g_connected; }

void ble_ndt_notify_measurement(const uint8_t *data, uint8_t len)
{
    if (!g_connected || len > sizeof(g_meas_data)) return;
    memcpy(g_meas_data, data, len);
    g_meas_len = len;
    ble_gatts_notify(g_conn_handle, g_chr_meas_val);
}

void ble_ndt_notify_ascan(const uint8_t *data, uint8_t len)
{
    if (!g_connected || len > sizeof(g_ascan_data)) return;
    memcpy(g_ascan_data, data, len);
    g_ascan_len = len;
    ble_gatts_notify(g_conn_handle, g_chr_ascan_val);
}

void ble_ndt_notify_status(uint8_t armed, uint8_t measuring, uint8_t bat)
{
    g_status_data[0] = armed;
    g_status_data[1] = measuring;
    g_status_data[2] = bat;
    g_status_data[3] = 0;
    if (g_connected)
        ble_gatts_notify(g_conn_handle, g_chr_status_val);
}

void ble_ndt_register_cmd(ble_cmd_cb_t cb) { g_cmd_cb = cb; }