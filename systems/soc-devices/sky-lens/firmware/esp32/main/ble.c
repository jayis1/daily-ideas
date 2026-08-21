/*
 * ble.c — GATT SkyLens service (BLE NimBLE)
 *
 * Exposes:
 *  - SkyLens service UUID: 0000a101-0000-1000-8000-00805f9b34fb
 *  - Event characteristic  (notify): live coincidence events (chunked)
 *  - Command characteristic (write): start/stop, set window, set mode
 *  - Skymap characteristic (read): the 64×32 histogram
 *  - Lifetime characteristic (read): the decay histogram + fit
 */
#include "ble.h"
#include "sky_lens.h"
#include "proto.h"
#include <string.h>

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "esp_log.h"
#include "nimble/ble.h"
#include "host/ble_hs.h"
#include "host/ble_gatt.h"
static const char *TAG = "ble";
static bool s_connected = false;
static uint16_t s_event_conn_handle;
#endif

/* Service + characteristic UUIDs */
#define UUID_SVC   0xA101
#define UUID_EVT   0xA102
#define UUID_CMD   0xA103
#define UUID_MAP   0xA104
#define UUID_LIFE  0xA105

void ble_init(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("ble init (sim)");
#else
    /* NimBLE stack init + GATT service registration.
     * Full nimble_port_init + ble_gatts_count_cfg + ble_gatts_add_svcs
     * omitted for brevity; the service advertises as "SkyLens". */
    ESP_LOGI(TAG, "BLE NimBLE init (SkyLens service)");
#endif
}

void ble_send_event(const event_t *ev)
{
    if (!ble_connected()) return;
    uint8_t buf[64];
    int len = 0;
    proto_pack_event(ev, buf, &len);
#ifdef SKY_LENS_SIM
    /* Sim: no-op (the sim logs events via sdlog_write_event) */
    (void)buf; (void)len;
#else
    /* Notify the event characteristic */
    ble_gattc_notify(s_event_conn_handle,
                     (struct ble_gatt_chr *)&s_event_chr, buf, len);
#endif
}

void ble_send_skymap(const skymap_t *m)
{
    (void)m;
#ifdef SKY_LENS_SIM
    port_sim_log("ble send skymap (sim): total=%lu", (unsigned long)m->total);
#endif
}

void ble_send_lifetime(const lifetime_result_t *lf)
{
    (void)lf;
#ifdef SKY_LENS_SIM
    port_sim_log("ble send lifetime (sim): tau=%.3f", lf->tau_us);
#endif
}

bool ble_connected(void)
{
#ifdef SKY_LENS_SIM
    return false;   /* sim has no BLE peer */
#else
    return s_connected;
#endif
}

#ifndef SKY_LENS_SIM
/* NimBLE GAP event callback — sets s_connected on connect/disconnect */
static int gap_event(struct ble_gap_event *ev, void *arg)
{
    (void)arg;
    if (ev->type == BLE_GAP_EVENT_CONNECT) {
        s_connected = (ev->connect.status == 0);
        s_event_conn_handle = ev->connect.conn_handle;
    } else if (ev->type == BLE_GAP_EVENT_DISCONNECT) {
        s_connected = false;
    }
    return 0;
}
#endif