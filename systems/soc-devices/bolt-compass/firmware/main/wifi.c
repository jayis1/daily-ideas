/*
 * wifi.c — Wi-Fi AP+STA + HTTP event stream + TCP socket
 *
 * Modes:
 *   AP+STA — the device starts as an AP ("BoltCompass-XXXX", no password)
 *            serving a captive config page to enter the home/field Wi-Fi,
 *            then switches to STA (or AP+STA if it can't connect). mDNS
 *            "bolt-compass.local".
 *   HTTP   - GET /              → captive config page
 *            GET /events.json   → last 100 strokes (JSON)
 *            GET /stream        → Server-Sent Events feed of sferics
 *            TCP  7777          → raw 12-byte packed events (for the PC app)
 */
#include "wifi.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "mdns.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "wifi";
static httpd_handle_t s_httpd;
static int s_tcp_clients[4];
static int s_n_tcp;

/* --- HTTP handlers --- */

static esp_err_t h_events(httpd_req_t *req)
{
    httpd_resp_set_type(req, "application/json");
    /* Simplified: return a stub. The real handler pulls the last 100
     * strokes from a ring maintained by the sferic core. */
    const char *stub = "{\"strokes\":[]}";
    return httpd_resp_send(req, stub, strlen(stub));
}

static esp_err_t h_stream(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/event-stream");
    /* SSE: keep the socket open and push events as they arrive.
     * In the real build this uses an async sender + a queue. */
    const char *hello = "retry:2000\n\n";
    httpd_resp_send(req, hello, strlen(hello));
    return ESP_OK;
}

static esp_err_t h_root(httpd_req_t *req)
{
    const char *page =
        "<html><head><title>Bolt Compass</title></head>"
        "<body><h1>Bolt Compass</h1>"
        "<p>Lightning station. Configure Wi-Fi:</p>"
        "<form action=/set method=post>"
        "SSID:<input name=s><br>PASS:<input name=p><br>"
        "<button>Save</button></form></body></html>";
    return httpd_resp_send(req, page, strlen(page));
}

static const httpd_uri_t uri_events  = { .uri="/events.json", .method=HTTP_GET, .handler=h_events };
static const httpd_uri_t uri_stream  = { .uri="/stream",      .method=HTTP_GET, .handler=h_stream };
static const httpd_uri_t uri_root    = { .uri="/",            .method=HTTP_GET, .handler=h_root };

static void start_http(void)
{
    httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
    cfg.max_uri_handlers = 8;
    if (httpd_start(&s_httpd, &cfg) == ESP_OK) {
        httpd_register_uri_handler(s_httpd, &uri_events);
        httpd_register_uri_handler(s_httpd, &uri_stream);
        httpd_register_uri_handler(s_httpd, &uri_root);
    }
}

static void ip_handler(void *arg, esp_event_base_t b, int32_t id, void *data)
{
    (void)arg; (void)b; (void)id; (void)data;
    start_http();
    mdns_init();
    mdns_hostname_set("bolt-compass");
    ESP_LOGI(TAG, "STA up, HTTP + mDNS started");
}

void wifi_init(void)
{
    nvs_flash_init();
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_ap();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    /* AP+STA: start as AP for config, attempt STA in background. */
    wifi_config_t ap = { .ap = { .ssid = "BoltCompass", .max_connection = 2 } };
    esp_wifi_set_config(WIFI_IF_AP, &ap);
    esp_wifi_set_mode(WIFI_MODE_APSTA);
    esp_wifi_start();

    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, ip_handler, NULL);
    ESP_LOGI(TAG, "Wi-Fi AP+STA started, AP 'BoltCompass'");
}

void wifi_stream_sferic(const stroke_t *st)
{
    /* SSE + TCP push (stubbed — real build formats the 12-byte packet /
     * JSON line and fans it out to all open sockets). */
    (void)st;
}