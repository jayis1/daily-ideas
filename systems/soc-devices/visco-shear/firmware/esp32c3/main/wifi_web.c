/*
 * visco-shear / firmware / esp32c3 / main / wifi_web.c
 * Wi-Fi softAP + HTTP server for Visco Shear web UI + CSV download
 *
 * AP: "Visco-Shear-XXXX" (no password)
 * Web UI: http://192.168.4.1/
 *   GET /            → Dashboard (live data, flow curve plot)
 *   GET /data        → Latest measurement JSON
 *   GET /download    → Download last CSV log
 *   GET /stream      → SSE live data stream
 *
 * MIT License.
 */
#include <string.h>
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_http_server.h"

#include "wifi_web.h"

static const char *TAG = "wifi_web";
static httpd_handle_t server = NULL;
static uint8_t latest_data[512];
static int latest_data_len = 0;

/* Simple HTML dashboard */
static const char *dashboard_html =
"<!DOCTYPE html><html><head><title>Visco Shear</title>"
"<meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
"<style>body{font-family:monospace;background:#1a1a2e;color:#eee;margin:20px}"
"canvas{background:#16213e;border:1px solid #0f3460}</style></head>"
"<body><h1>Visco Shear</h1>"
"<p>Live rheology data from your pocket rheometer.</p>"
"<canvas id='chart' width='600' height='300'></canvas>"
"<div id='result'>Waiting for data...</div>"
"<p><a href='/download'>Download CSV</a> | <a href='/stream'>Live stream</a></p>"
"<script>"
"var ws=new EventSource('/stream');"
"ws.onmessage=function(e){document.getElementById('result').textContent=e.data;};"
"</script></body></html>";

static esp_err_t handler_root(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, dashboard_html, strlen(dashboard_html));
    return ESP_OK;
}

static esp_err_t handler_data(httpd_req_t *req)
{
    httpd_resp_set_type(req, "application/json");
    if (latest_data_len > 0) {
        httpd_resp_send(req, (char *)latest_data, latest_data_len);
    } else {
        httpd_resp_send(req, "{\"status\":\"no_data\"}", 20);
    }
    return ESP_OK;
}

static esp_err_t handler_download(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/csv");
    httpd_resp_set_hdr(req, "Content-Disposition",
                       "attachment; filename=visco_shear_log.csv");
    /* In production: read from SD via RP2040 or SPI flash */
    const char *csv = "# Visco Shear CSV log\n# No data yet\n";
    httpd_resp_send(req, csv, strlen(csv));
    return ESP_OK;
}

static esp_err_t handler_stream(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/event-stream");
    httpd_resp_set_hdr(req, "Cache-Control", "no-cache");
    /* SSE: send keepalive (in production, stream live data) */
    const char *sse = "data: Visco Shear live stream\\n\\n";
    httpd_resp_send(req, sse, strlen(sse));
    return ESP_OK;
}

static void start_webserver(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.max_uri_handlers = 8;

    if (httpd_start(&server, &config) == ESP_OK) {
        httpd_uri_t uri_root = { .uri = "/", .method = HTTP_GET, .handler = handler_root };
        httpd_uri_t uri_data = { .uri = "/data", .method = HTTP_GET, .handler = handler_data };
        httpd_uri_t uri_dl   = { .uri = "/download", .method = HTTP_GET, .handler = handler_download };
        httpd_uri_t uri_str  = { .uri = "/stream", .method = HTTP_GET, .handler = handler_stream };

        httpd_register_uri_handler(server, &uri_root);
        httpd_register_uri_handler(server, &uri_data);
        httpd_register_uri_handler(server, &uri_dl);
        httpd_register_uri_handler(server, &uri_str);

        ESP_LOGI(TAG, "Web server started on port %d", config.server_port);
    }
}

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                              int32_t event_id, void *event_data)
{
    if (event_id == WIFI_EVENT_AP_START) {
        ESP_LOGI(TAG, "Wi-Fi AP started: Visco-Shear");
        start_webserver();
    }
}

void wifi_web_init(void)
{
    /* Init NVS */
    esp_err_t ret = nvs_flash_init();
    if (ret != ESP_OK) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Init Wi-Fi AP */
    esp_netif_create_default_wifi_ap();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                        wifi_event_handler, NULL, NULL);

    wifi_config_t wifi_cfg = {
        .ap = {
            .ssid = "Visco-Shear",
            .ssid_len = strlen("Visco-Shear"),
            .channel = 1,
            .max_connection = 4,
            .authmode = WIFI_AUTH_OPEN,
        },
    };
    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &wifi_cfg);
    esp_wifi_start();

    ESP_LOGI(TAG, "Wi-Fi AP: 'Visco-Shear' (open), connect to http://192.168.4.1/");
}

void wifi_web_push_data(const uint8_t *data, int len)
{
    /* Store latest data for /data endpoint */
    if (len > (int)sizeof(latest_data)) len = sizeof(latest_data);
    memcpy(latest_data, data, len);
    latest_data_len = len;
}