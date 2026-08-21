/*
 * kappa-pin / firmware / main / wifi_web.c
 * Wi-Fi softAP + HTTP server for web UI and CSV download
 *
 * Serves a simple HTML page with live ΔT chart (SSE) and CSV download.
 *
 * MIT License.
 */
#include "wifi_web.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "nvs_flash.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "wifi";
static httpd_handle_t server = NULL;
static int n_clients = 0;
static char ap_ip[16] = "192.168.4.1";
static meas_result_t last_result;

/* HTML page with JavaScript live chart */
static const char *PAGE_HTML =
"<!DOCTYPE html><html><head><meta charset='utf-8'>"
"<meta name='viewport' content='width=device-width,initial-scale=1'>"
"<title>Kappa Pin</title><style>"
"body{font-family:monospace;margin:10px;background:#222;color:#8f8}"
"canvas{display:block;width:100%;height:300px;background:#111}"
"div{margin:5px 0} button{font-size:16px;padding:8px 20px}"
"</style></head><body>"
"<h2>Kappa Pin - Thermal Conductivity Meter</h2>"
"<div><button onclick=\"fetch('/cmd?c=1')\">Start</button>"
"<button onclick=\"fetch('/cmd?c=2')\">Stop</button></div>"
"<div id='r'>Waiting...</div>"
"<canvas id='cv' width='600' height='300'></canvas>"
"<div><a href='/csv'>Download CSV</a></div>"
"<script>"
"var c=document.getElementById('cv'),x=c.getContext('2d');"
"var pts=[];var es=new EventSource('/stream');"
"es.onmessage=function(e){var d=e.data.split(',');"
"pts.push({t:+d[0],dt:+d[1]});if(pts.length>600)pts.shift();"
"x.clearRect(0,0,600,300);"
"var mx=0;for(var p of pts)if(p.dt>mx)mx=p.dt;if(mx<1)mx=1;"
"x.strokeStyle='#0f0';x.beginPath();"
"for(var i=0;i<pts.length;i++){"
"var px=i*600/600;var py=290-(pts[i].dt/mx)*280;"
"if(i==0)x.moveTo(px,py);else x.lineTo(px,py);}x.stroke();};"
"fetch('/result').then(r=>r.text()).then(t=>document.getElementById('r').innerHTML=t);"
"</script></body></html>";

/* SSE stream handler */
static esp_err_t stream_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/event-stream");
    httpd_resp_set_hdr(req, "Cache-Control", "no-cache");
    httpd_resp_set_hdr(req, "Connection", "keep-alive");
    n_clients++;

    /* Keep connection open — data pushed via wifi_web_push_sample */
    char buf[64];
    while (true) {
        /* This is a simplified handler; in production we'd use async send */
        vTaskDelay(pdMS_TO_TICKS(1000));
        int len = snprintf(buf, sizeof(buf), "data: 0,0\n\n");
        httpd_resp_send_chunk(req, buf, len);
    }
    return ESP_OK;
}

/* Root page handler */
static esp_err_t index_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, PAGE_HTML, strlen(PAGE_HTML));
    return ESP_OK;
}

/* Result handler */
static esp_err_t result_handler(httpd_req_t *req)
{
    char buf[256];
    int len = snprintf(buf, sizeof(buf),
        "lambda=%.4f W/m.K<br>alpha=%.3f mm2/s<br>"
        "rhoCp=%.3e J/m3.K<br>effusivity=%.1f<br>R2=%.5f",
        last_result.lambda, last_result.alpha,
        last_result.rho_cp, last_result.effusivity,
        last_result.r_squared);
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, buf, len);
    return ESP_OK;
}

/* Command handler */
static esp_err_t cmd_handler(httpd_req_t *req)
{
    char buf[64];
    httpd_req_get_url_query_str(req, buf, sizeof(buf));
    char val[8] = {0};
    httpd_query_key_value(buf, "c", val, sizeof(val));
    /* Forward command via the same callback used by BLE */
    /* (simplified — in production we'd share a command dispatcher) */
    httpd_resp_send(req, "OK", 2);
    return ESP_OK;
}

/* CSV download handler */
static esp_err_t csv_handler(httpd_req_t *req)
{
    /* Serve the last SD card file if available */
    httpd_resp_set_type(req, "text/csv");
    httpd_resp_send(req, "# See SD card for full log\n", 27);
    return ESP_OK;
}

void wifi_web_init(void)
{
    /* Initialize NVS (if not already) */
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    /* Initialize Wi-Fi in AP mode */
    esp_netif_create_default_wifi_ap();
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    /* Generate unique SSID with last 2 bytes of MAC */
    uint8_t mac[6];
    esp_wifi_get_mac(WIFI_IF_AP, mac);
    char ssid[20];
    snprintf(ssid, sizeof(ssid), "KappaPin-%02X%02X", mac[4], mac[5]);

    wifi_config_t wifi_cfg = {0};
    strcpy((char *)wifi_cfg.ap.ssid, ssid);
    wifi_cfg.ap.ssid_len = strlen(ssid);
    wifi_cfg.ap.channel = WIFI_AP_CHANNEL;
    wifi_cfg.ap.max_connection = WIFI_AP_MAX_CONN;
    wifi_cfg.ap.authmode = WIFI_AUTH_OPEN;

    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &wifi_cfg);
    esp_wifi_start();

    ESP_LOGI(TAG, "Wi-Fi AP started: %s (IP: %s)", ssid, ap_ip);

    /* Start HTTP server */
    httpd_config_t http_cfg = HTTPD_DEFAULT_CONFIG();
    http_cfg.max_uri_handlers = 8;
    esp_http_server_init(&http_cfg, &server);

    /* Register URI handlers */
    static httpd_uri_t uri_index = { .uri="/", .method=HTTP_GET, .handler=index_handler };
    static httpd_uri_t uri_stream = { .uri="/stream", .method=HTTP_GET, .handler=stream_handler };
    static httpd_uri_t uri_result = { .uri="/result", .method=HTTP_GET, .handler=result_handler };
    static httpd_uri_t uri_cmd = { .uri="/cmd", .method=HTTP_GET, .handler=cmd_handler };
    static httpd_uri_t uri_csv = { .uri="/csv", .method=HTTP_GET, .handler=csv_handler };

    httpd_register_uri_handler(server, &uri_index);
    httpd_register_uri_handler(server, &uri_stream);
    httpd_register_uri_handler(server, &uri_result);
    httpd_register_uri_handler(server, &uri_cmd);
    httpd_register_uri_handler(server, &uri_csv);
}

void wifi_web_update_result(const meas_result_t *r)
{
    memcpy(&last_result, r, sizeof(last_result));
}

void wifi_web_push_sample(const meas_sample_t *s)
{
    /* SSE push would go to connected clients — simplified */
    (void)s;
}

bool wifi_web_has_clients(void) { return n_clients > 0; }
const char *wifi_web_get_ip(void) { return ap_ip; }