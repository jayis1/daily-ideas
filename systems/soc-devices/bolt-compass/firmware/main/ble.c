/*
 * ble.c — NimBLE BoltCompass GATT service
 *
 * Service UUID:  0xB07C  ("Bolt Compass")
 * Characteristics:
 *   0xB071  SfericEvent    (notify, 12 bytes)  — packed stroke summary
 *   0xB072  SfericWaveform (notify, chunked)   — 20-byte chunks of the 50 ms window
 *   0xB073  StormAlert     (notify, 1 byte)
 *   0xB074  Command        (write)             — START / STOP / CALIBRATE
 *
 * Packed 12-byte SfericEvent:
 *   u32 ts_lo (seconds since PPS epoch, low 32 bits)
 *   u8  type (0=CG,1=IC,2=CC)
 *   u8  conf (0..255 = conf*255)
 *   u16 bearing (0..36000 = deg*100)
 *   u16 distance_km (0..65000)
 *   u16 peak_uv
 *   u8  flash_rate
 *   u8  reserved
 */
#include "ble.h"
#include "esp_log.h"
#include "host/ble_hs.h"
#include "host/ble_uuid.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include <string.h>

static const char *TAG = "ble";

static uint16_t s_conn_handle = BLE_HS_CONN_HANDLE_NONE;
static uint16_t s_chr_event;
static uint16_t s_chr_alert;

/* Access callbacks (simplified — full NimBLE attr table in real HW). */
static int gatt_access(uint16_t conn, uint16_t attr,
                       struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    (void)conn; (void)attr; (void)ctxt; (void)arg;
    return 0;
}

static int gap_event(struct ble_gap_event *ev, void *arg)
{
    (void)arg;
    switch (ev->type) {
    case BLE_GAP_EVENT_CONNECT:
        s_conn_handle = ev->connect.conn_handle;
        ESP_LOGI(TAG, "BLE connected h=%d", s_conn_handle);
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        s_conn_handle = BLE_HS_CONN_HANDLE_NONE;
        ESP_LOGI(TAG, "BLE disconnected");
        break;
    default: break;
    }
    return 0;
}

static void start_adv(void)
{
    struct ble_hs_adv_fields f = {0};
    const char *name = "BoltCompass";
    f.name = (uint8_t *)name;
    f.name_len = strlen(name);
    f.name_is_complete = 1;
    ble_gap_adv_set_fields(&f);

    struct ble_gap_adv_params p = {0};
    ble_gap_adv_start(ble_addr_any(), NULL, BLE_HS_FOREVER, &p, gap_event, NULL);
}

static void sync_cb(void) { start_adv(); }

static void host_task(void *p) { nimble_port_run(); (void)p; }

void ble_init(void)
{
    esp_err_t err = nimble_port_init();
    if (err) { ESP_LOGE(TAG, "nimble init %s", esp_err_to_name(err)); return; }

    /* GATT service (simplified — real build uses ble_svc_reg + attr table). */
    struct ble_gatt_svc_def svcs[] = {
        { .type = BLE_GATT_SVC_TYPE_PRIMARY,
          .uuid = BLE_UUID16_DECLARE(0xB07C),
          .characteristics = (struct ble_gatt_chr_def[]) {
            { .uuid = BLE_UUID16_DECLARE(0xB071),
              .flags = BLE_GATT_CHR_F_NOTIFY,
              .access_cb = gatt_access, .val_handle = &s_chr_event },
            { .uuid = BLE_UUID16_DECLARE(0xB073),
              .flags = BLE_GATT_CHR_F_NOTIFY,
              .access_cb = gatt_access, .val_handle = &s_chr_alert },
            { 0 }
          }
        },
        { 0 }
    };
    ble_svc_gap_init();
    ble_svc_gatt_init();
    ble_svc_reg(svcs);
    ble_hs_cfg.sync_cb = sync_cb;
    ble_svc_gap_device_name_set("BoltCompass");

    nimble_port_freertos_init(host_task);
    ESP_LOGI(TAG, "BoltCompass BLE service 0xB07C");
}

static void notify_packed(uint16_t chr, const uint8_t *data, int len)
{
    if (s_conn_handle == BLE_HS_CONN_HANDLE_NONE) return;
    struct os_mbuf *om = ble_hs_mbuf_from_flat(data, len);
    if (om) ble_gattc_notify_custom(s_conn_handle, chr, om);
}

void ble_notify_sferic(const stroke_t *st)
{
    uint8_t pkt[12];
    uint32_t ts_lo = (uint32_t)(st->ts_us / 1000000ULL);
    uint16_t brg   = (uint16_t)(st->geo.azimuth_deg * 100.0f);
    uint16_t dist  = (uint16_t)st->geo.distance_km;
    uint16_t peak  = (uint16_t)st->geo.peak_field_uv;
    pkt[0]  = ts_lo & 0xFF; pkt[1] = (ts_lo>>8)&0xFF;
    pkt[2]  = (ts_lo>>16)&0xFF; pkt[3] = (ts_lo>>24)&0xFF;
    pkt[4]  = (uint8_t)st->cls.label;
    pkt[5]  = (uint8_t)(st->cls.conf * 255.0f);
    pkt[6]  = brg & 0xFF;   pkt[7] = (brg>>8)&0xFF;
    pkt[8]  = dist & 0xFF;  pkt[9] = (dist>>8)&0xFF;
    pkt[10] = peak & 0xFF;  pkt[11] = (peak>>8)&0xFF;
    notify_packed(s_chr_event, pkt, 12);
}

void ble_notify_alert(alert_t a)
{
    uint8_t p = (uint8_t)a;
    notify_packed(s_chr_alert, &p, 1);
}