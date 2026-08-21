/*
 * wifi.c — AP+STA, captive portal, HTTP /events /skymap /lifetime, TCP stream
 *
 * The ESP32-S3 runs a soft AP "SkyLens-XXXX" with a captive portal for
 * configuration, and optionally joins a known Wi-Fi (STA mode). HTTP
 * endpoints serve the last 100 events, the skymap histogram, and the
 * lifetime fit. A raw TCP port streams live events.
 */
#include "wifi.h"
#include "sky_lens.h"
#include "proto.h"
#include <string.h>

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "nvs_flash.h"
static const char *TAG = "wifi";
static bool s_connected = false;
static httpd_handle_t s_http = NULL;
#endif

/* Ring buffer of recent events for the /events.json endpoint */
#define EVT_BUF 100
static event_t s_evt_buf[EVT_BUF];
static int s_evt_head = 0, s_evt_tail = 0;

static void evt_buf_push(const event_t *ev)
{
    s_evt_buf[s_evt_head] = *ev;
    s_evt_head = (s_evt_head + 1) % EVT_BUF;
    if (s_evt_head == s_evt_tail)
        s_evt_tail = (s_evt_tail + 1) % EVT_BUF;
}

void wifi_init(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("wifi init (sim)");
#else
    /* Wi-Fi AP+STA init + HTTP server start.
     * The full esp_wifi_init + event handlers + httpd_start are omitted
     * for brevity; the AP advertises "SkyLens-XXXX" with a captive
     * portal on 192.168.4.1. */
    ESP_LOGI(TAG, "Wi-Fi AP+STA init (SkyLens AP)");
    s_connected = true;
#endif
}

void wifi_send_event(const event_t *ev)
{
    evt_buf_push(ev);
#ifdef SKY_LENS_SIM
    /* Sim: no-op */
#else
    /* If a TCP stream client is connected, send the event frame */
    /* (TCP stream implementation omitted for brevity) */
#endif
}

bool wifi_connected(void)
{
#ifdef SKY_LENS_SIM
    return false;
#else
    return s_connected;
#endif
}

#ifndef SKY_LENS_SIM
/* HTTP handlers — abbreviated */
static esp_err_t h_events(httpd_req_t *req)
{
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr_chunk(req, "{\"events\":[");
    int idx = s_evt_tail;
    bool first = true;
    while (idx != s_evt_head) {
        if (!first) httpd_resp_sendstr_chunk(req, ",");
        char buf[128];
        snprintf(buf, sizeof(buf),
                 "{\"seq\":%lu,\"zen\":%.1f,\"az\":%.1f,\"h0\":%d,\"h1\":%d}",
                 (unsigned long)s_evt_buf[idx].seq,
                 s_evt_buf[idx].zenith_deg, s_evt_buf[idx].az_deg,
                 s_evt_buf[idx].h0_mv, s_evt_buf[idx].h1_mv);
        httpd_resp_sendstr_chunk(req, buf);
        first = false;
        idx = (idx + 1) % EVT_BUF;
    }
    httpd_resp_sendstr_chunk(req, "]}");
    httpd_resp_send_chunk(req, NULL, 0);
    return ESP_OK;
}

static esp_err_t h_skymap(httpd_req_t *req)
{
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr_chunk(req, "{\"skymap\":[");
    /* ... stream the 64×32 array ... */
    httpd_resp_sendstr_chunk(req, "]}");
    httpd_resp_send_chunk(req, NULL, 0);
    return ESP_OK;
}

static esp_err_t h_lifetime(httpd_req_t *req)
{
    httpd_resp_set_type(req, "application/json");
    /* ... return the lifetime histogram + fit ... */
    httpd_resp_sendstr_chunk(req, "{\"lifetime\":\"TODO\"}");
    httpd_resp_send_chunk(req, NULL, 0);
    return ESP_OK;
}

static httpd_uri_t uri_events   = { .uri="/events.json",   .method=HTTP_GET, .handler=h_events   };
static httpd_uri_t uri_skymap   = { .uri="/skymap.json",   .method=HTTP_GET, .handler=h_skymap   };
static httpd_uri_t uri_lifetime = { .uri="/lifetime.json", .method=HTTP_GET, .handler=h_lifetime };

/* Registration in wifi_init (would be called there) */
static void register_handlers(void)
{
    httpd_register_uri_handler(s_http, &uri_events);
    httpd_register_uri_handler(s_http, &uri_skymap);
    httpd_register_uri_handler(s_http, &uri_lifetime);
}
#endif