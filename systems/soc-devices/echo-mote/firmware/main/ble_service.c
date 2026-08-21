/**
 * ble_service.c — BLE 5.0 GATT server
 *
 * Service UUID: 0xFFB0 (EchoMote)
 * Characteristics:
 *   0xFFB1: Measurement Command (write)
 *   0xFFB2: RT60 Results (read/notify)
 *   0xFFB3: Freq Response (read)
 *   0xFFB4: Room Modes (read/notify)
 *   0xFFB5: Clarity (read/notify)
 *   0xFFB6: NC Curve (read)
 *   0xFFB7: Device Status (read/notify)
 *   0xFFB8: Battery Level (read)
 */

#include "ble_service.h"
#include <string.h>
#include "esp_log.h"
#include "host/ble_hs.h"
#include "host/ble_gatt.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

static const char *TAG = "ble";

/* Device status */
static uint8_t device_status = 0;  /* 0=idle, 1=measuring, 2=streaming */
static uint8_t battery_level = 100;

/* Stored results (accessible via GATT reads) */
static acoustic_results_t last_results;
static uint32_t last_mode = 0;
static bool client_connected = false;

/* Connection handle */
static uint16_t conn_handle = 0;

/* Characteristic value buffers */
static uint8_t rt60_buf[24];         /* 6 × float32 */
static uint8_t freq_buf[240];        /* 60 × float32 (subset of 31 1/3-oct bands) */
static uint8_t modes_buf[32];        /* 8 × {freq_u16, decay_u16, type_u8} */
static uint8_t clarity_buf[28];      /* 6 × C50 + 6 × C80 (int8 dB) */
static uint8_t nc_buf[32];           /* 16 × uint8 dB SPL */
static uint8_t status_buf[1];
static uint8_t battery_buf[1];

/* GATT access callbacks */
static int access_rt60(uint16_t conn_handle, uint16_t attr_handle,
                        struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_freq(uint16_t conn_handle, uint16_t attr_handle,
                        struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_modes(uint16_t conn_handle, uint16_t attr_handle,
                         struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_clarity(uint16_t conn_handle, uint16_t attr_handle,
                           struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_nc(uint16_t conn_handle, uint16_t attr_handle,
                      struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_command(uint16_t conn_handle, uint16_t attr_handle,
                           struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_status(uint16_t conn_handle, uint16_t attr_handle,
                          struct ble_gatt_access_ctxt *ctxt, void *arg);
static int access_battery(uint16_t conn_handle, uint16_t attr_handle,
                           struct ble_gatt_access_ctxt *ctxt, void *arg);

/* GATT service definition */
static const struct ble_gatt_svc_def gatt_svr_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(0xFFB0),
        .characteristics = (struct ble_gatt_chr_def[]) {
            {
                .uuid = BLE_UUID16_DECLARE(0xFFB1),
                .access_cb = access_command,
                .flags = BLE_GATT_CHR_F_WRITE,
            },
            {
                .uuid = BLE_UUID16_DECLARE(0xFFB2),
                .access_cb = access_rt60,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
            },
            {
                .uuid = BLE_UUID16_DECLARE(0xFFB3),
                .access_cb = access_freq,
                .flags = BLE_GATT_CHR_F_READ,
            },
            {
                .uuid = BLE_UUID16_DECLARE(0xFFB4),
                .access_cb = access_modes,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
            },
            {
                .uuid = BLE_UUID16_DECLARE(0xFFB5),
                .access_cb = access_clarity,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
            },
            {
                .uuid = BLE_UUID16_DECLARE(0xFFB6),
                .access_cb = access_nc,
                .flags = BLE_GATT_CHR_F_READ,
            },
            {
                .uuid = BLE_UUID16_DECLARE(0xFFB7),
                .access_cb = access_status,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
            },
            {
                .uuid = BLE_UUID16_DECLARE(0xFFB8),
                .access_cb = access_battery,
                .flags = BLE_GATT_CHR_F_READ,
            },
            { 0 }  /* Terminator */
        },
    },
    { 0 }  /* Terminator */
};

/* Access callback implementations */
static int access_rt60(uint16_t ch, uint16_t ah,
                        struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, rt60_buf, sizeof(rt60_buf));
    }
    return 0;
}

static int access_freq(uint16_t ch, uint16_t ah,
                        struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, freq_buf, sizeof(freq_buf));
    }
    return 0;
}

static int access_modes(uint16_t ch, uint16_t ah,
                         struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, modes_buf, sizeof(modes_buf));
    }
    return 0;
}

static int access_clarity(uint16_t ch, uint16_t ah,
                           struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, clarity_buf, sizeof(clarity_buf));
    }
    return 0;
}

static int access_nc(uint16_t ch, uint16_t ah,
                      struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        os_mbuf_append(ctxt->om, nc_buf, sizeof(nc_buf));
    }
    return 0;
}

static int access_command(uint16_t ch, uint16_t ah,
                           struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint8_t cmd = 0;
        os_mbuf_copydata(ctxt->om, 0, 1, &cmd);
        ESP_LOGI(TAG, "BLE command: %d", cmd);
        /* Command triggers measurement — handled by app_main */
    }
    return 0;
}

static int access_status(uint16_t ch, uint16_t ah,
                          struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        status_buf[0] = device_status;
        os_mbuf_append(ctxt->om, status_buf, 1);
    }
    return 0;
}

static int access_battery(uint16_t ch, uint16_t ah,
                           struct ble_gatt_access_ctxt *ctxt, void *arg) {
    if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
        battery_buf[0] = battery_level;
        os_mbuf_append(ctxt->om, battery_buf, 1);
    }
    return 0;
}

/* GAP connection callback */
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
    case BLE_GAP_EVENT_ADV_COMPLETE:
        /* Restart advertising */
        break;
    default:
        break;
    }
}

/* BLE host task */
static void ble_host_task(void *param) {
    nimble_port_run();
    nimble_port_freertos_deinit();
}

int ble_service_init(void) {
    ESP_LOGI(TAG, "Initializing BLE service");

    nimble_port_init();
    ble_svc_gap_init();
    ble_svc_gatt_init();

    ble_gatts_count_cfg(gatt_svr_svcs);
    ble_gatts_add_svcs(gatt_svr_svcs);

    /* Set device name */
    ble_svc_gap_device_name_set("EchoMote");

    /* Start advertising */
    struct ble_gap_adv_params adv_params = {
        .conn_mode = BLE_GAP_CONN_MODE_UND,
        .disc_mode = BLE_GAP_DISC_MODE_GEN,
        .itvl_min = 0x0020,  /* 20 ms */
        .itvl_max = 0x0040,  /* 40 ms */
    };

    uint8_t adv_data[] = {
        0x02, 0x01, 0x06,             /* Flags */
        0x03, 0x03, 0xB0, 0xFF,       /* Complete 16-bit UUID: 0xFFB0 */
        0x04, 0xFF, 0x00, device_status, battery_level,  /* Mfr-specific */
    };

    ble_gap_adv_set_data(adv_data, sizeof(adv_data));
    ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER,
                      &adv_params, on_gap_event, NULL);

    nimble_port_freertos_init(ble_host_task);

    return 0;
}

int ble_service_notify_results(uint32_t mode, const acoustic_results_t *results) {
    last_results = *results;
    last_mode = mode;
    device_status = 0;  /* idle */

    /* Pack RT60 into notify buffer */
    for (int i = 0; i < 6; i++) {
        uint32_t val;
        memcpy(&val, &results->rt60[i], 4);
        rt60_buf[i * 4] = val & 0xFF;
        rt60_buf[i * 4 + 1] = (val >> 8) & 0xFF;
        rt60_buf[i * 4 + 2] = (val >> 16) & 0xFF;
        rt60_buf[i * 4 + 3] = (val >> 24) & 0xFF;
    }

    /* Pack room modes */
    memset(modes_buf, 0, sizeof(modes_buf));
    for (int i = 0; i < results->num_modes && i < 8; i++) {
        uint16_t freq = (uint16_t)results->room_modes[i].freq;
        uint16_t decay = (uint16_t)(results->room_modes[i].decay_time * 100);
        uint8_t type = results->room_modes[i].type;
        modes_buf[i * 4] = freq & 0xFF;
        modes_buf[i * 4 + 1] = (freq >> 8) & 0xFF;
        modes_buf[i * 4 + 2] = decay & 0xFF;
        modes_buf[i * 4 + 3] = (decay >> 8) << 4 | (type & 0x0F);
    }

    /* Pack clarity (C50 + C80 as int8 dB values) */
    for (int i = 0; i < 6; i++) {
        clarity_buf[i] = (int8_t)results->c50[i];
        clarity_buf[i + 6] = (int8_t)results->c80[i];
    }

    /* Pack NC curve */
    for (int i = 0; i < 8 && i < 16; i++) {
        nc_buf[i] = (uint8_t)results->nc_bands[i];
    }

    /* Send notifications if client connected */
    if (client_connected && conn_handle) {
        struct os_mbuf *om;
        uint16_t attr_handle;

        /* Notify RT60 */
        om = ble_hs_mbuf_from_flat(rt60_buf, sizeof(rt60_buf));
        ble_gatts_notify_custom(conn_handle,
                                ble_gatt_chr_val_handle(0), om);

        /* Notify status */
        status_buf[0] = device_status;
        om = ble_hs_mbuf_from_flat(status_buf, 1);
        ble_gatts_notify_custom(conn_handle,
                                ble_gatt_chr_val_handle(6), om);
    }

    return 0;
}

bool ble_service_is_connected(void) {
    return client_connected;
}