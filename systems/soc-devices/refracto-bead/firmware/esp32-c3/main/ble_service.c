/**
 * ble_service.c — BLE 5.0 GATT server for Refracto Bead
 *
 * Service UUID: 0xFFC0 (RefractoBead)
 *   0xFFC1: Measurement Command (write)
 *   0xFFC2: RI Results (read/notify)
 *   0xFFC3: Derived Results (read/notify)
 *   0xFFC4: Compound Match (read/notify)
 *   0xFFC5: Raw CCD Waveform (read)
 *   0xFFC6: Device Status (read/notify)
 *   0xFFC7: Battery Level (read)
 *   0xFFC8: Library Entry (read/write)
 */

#include "ble_service.h"
#include "uart_protocol.h"
#include <string.h>
#include "esp_log.h"
#include "host/ble_hs.h"
#include "host/ble_gatt.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *TAG = "ble";

static uint8_t device_status = 0;
static uint8_t battery_level = 100;
static bool client_connected = false;
static uint16_t conn_handle = 0;

static ri_result_t last_result;
static uint8_t ri_buf[32];
static uint8_t derived_buf[20];
static uint8_t compound_buf[48];

/* Access callbacks */
static int access_cmd(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_ri(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_derived(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_compound(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_waveform(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_status(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_battery(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_library(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg);

static const struct ble_gatt_svc_def gatt_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(0xFFC0),
        .characteristics = (struct ble_gatt_chr_def[]) {
            { .uuid = BLE_UUID16_DECLARE(0xFFC1), .access_cb = access_cmd,
              .flags = BLE_GATT_CHR_F_WRITE },
            { .uuid = BLE_UUID16_DECLARE(0xFFC2), .access_cb = access_ri,
              .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY },
            { .uuid = BLE_UUID16_DECLARE(0xFFC3), .access_cb = access_derived,
              .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY },
            { .uuid = BLE_UUID16_DECLARE(0xFFC4), .access_cb = access_compound,
              .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY },
            { .uuid = BLE_UUID16_DECLARE(0xFFC5), .access_cb = access_waveform,
              .flags = BLE_GATT_CHR_F_READ },
            { .uuid = BLE_UUID16_DECLARE(0xFFC6), .access_cb = access_status,
              .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY },
            { .uuid = BLE_UUID16_DECLARE(0xFFC7), .access_cb = access_battery,
              .flags = BLE_GATT_CHR_F_READ },
            { .uuid = BLE_UUID16_DECLARE(0xFFC8), .access_cb = access_library,
              .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE },
            { 0 }
        },
    },
    { 0 }
};

static int access_cmd(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t cmd = 0;
        os_mbuf_copydata(ctxt->om, 0, 1, &cmd);
        ESP_LOGI(TAG, "BLE command: %d", cmd);
        /* Commands are forwarded to STM32 via UART (not implemented here) */
    }
    return 0;
}

static int access_ri(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, ri_buf, sizeof(ri_buf));
    }
    return 0;
}

static int access_derived(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, derived_buf, sizeof(derived_buf));
    }
    return 0;
}

static int access_compound(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, compound_buf, sizeof(compound_buf));
    }
    return 0;
}

static int access_waveform(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        /* Return 256 bytes of raw CCD data (not implemented — would request from STM32) */
        uint8_t dummy[256] = {0};
        os_mbuf_append(ctxt->om, dummy, 256);
    }
    return 0;
}

static int access_status(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, &device_status, 1);
    }
    return 0;
}

static int access_battery(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, &battery_level, 1);
    }
    return 0;
}

static int access_library(uint16_t ch, uint16_t ah, struct ble_gatt_access_ctxt *ctxt, void *arg) {
    /* Library entry read/write — simplified */
    return 0;
}

static void on_gap_event(struct ble_gap_event *event, void *arg) {
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        if (event->connect.status == 0) {
            conn_handle = event->connect.conn_handle;
            client_connected = true;
            ESP_LOGI(TAG, "BLE client connected");
        } else {
            client_connected = false;
        }
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        client_connected = false;
        conn_handle = 0;
        ESP_LOGI(TAG, "BLE client disconnected");
        /* Restart advertising */
        ble_service_init();
        break;
    default:
        break;
    }
}

static void ble_host_task(void *param) {
    nimble_port_run();
    nimble_port_freertos_deinit();
}

int ble_service_init(void) {
    ESP_LOGI(TAG, "Initializing BLE service");

    nimble_port_init();
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_gatts_count_cfg(gatt_svcs);
    ble_gatts_add_svcs(gatt_svcs);

    ble_svc_gap_device_name_set("RefractoBead");

    struct ble_gap_adv_params adv = {
        .conn_mode = BLE_GAP_CONN_MODE_UND,
        .disc_mode = BLE_GAP_DISC_MODE_GEN,
        .itvl_min = 0x0020,
        .itvl_max = 0x0040,
    };

    uint16_t nd_raw = (uint16_t)(last_result.n_D * 10000);
    uint8_t adv_data[] = {
        0x02, 0x01, 0x06,
        0x03, 0x03, 0xC0, 0xFF,
        0x05, 0xFF, 0x00, device_status, battery_level,
        nd_raw & 0xFF, (nd_raw >> 8) & 0xFF,
    };
    ble_gap_adv_set_data(adv_data, sizeof(adv_data));
    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &adv, on_gap_event, NULL);

    nimble_port_freertos_init(ble_host_task);
    return 0;
}

void ble_service_notify_result(const ri_result_t *result) {
    last_result = *result;

    /* Pack RI results: n_D, n_F, n_C, V_D, T_prism (5 × float32 = 20 bytes) + 12 padding */
    memset(ri_buf, 0, sizeof(ri_buf));
    memcpy(&ri_buf[0], &result->n_D, 4);
    memcpy(&ri_buf[4], &result->n_F, 4);
    memcpy(&ri_buf[8], &result->n_C, 4);
    memcpy(&ri_buf[12], &result->abbe_vd, 4);
    memcpy(&ri_buf[16], &result->t_prism, 4);
    memcpy(&ri_buf[20], &result->dispersion, 4);

    /* Pack derived: brix, sg, abv, fp (4 × float32 = 16) + compound_id (1) + 3 pad */
    memcpy(&derived_buf[0], &result->brix, 4);
    memcpy(&derived_buf[4], &result->specific_grav, 4);
    memcpy(&derived_buf[8], &result->abv, 4);
    memcpy(&derived_buf[12], &result->freeze_point, 4);
    derived_buf[16] = (uint8_t)result->compound_id;

    /* Pack compound match: name[16] + n_D + V_D + confidence + rank (32 bytes × 1, simplified) */
    memset(compound_buf, 0, sizeof(compound_buf));
    memcpy(&compound_buf[0], result->compound_name, 16);
    memcpy(&compound_buf[16], &result->n_D, 4);
    memcpy(&compound_buf[20], &result->abbe_vd, 4);
    memcpy(&compound_buf[24], &result->confidence, 4);

    if (client_connected && conn_handle) {
        struct os_mbuf *om;

        om = ble_hs_mbuf_from_flat(ri_buf, sizeof(ri_buf));
        ble_gatts_notify_custom(conn_handle, 0, om);

        om = ble_hs_mbuf_from_flat(derived_buf, sizeof(derived_buf));
        ble_gatts_notify_custom(conn_handle, 0, om);

        om = ble_hs_mbuf_from_flat(compound_buf, sizeof(compound_buf));
        ble_gatts_notify_custom(conn_handle, 0, om);
    }
}

void ble_service_notify_status(uint8_t status, uint8_t battery) {
    device_status = status;
    battery_level = battery;
    if (client_connected && conn_handle) {
        struct os_mbuf *om = ble_hs_mbuf_from_flat(&device_status, 1);
        ble_gatts_notify_custom(conn_handle, 0, om);
    }
}

bool ble_service_is_connected(void) {
    return client_connected;
}