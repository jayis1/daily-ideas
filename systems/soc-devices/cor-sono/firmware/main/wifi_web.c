/*
 * cor-sono / firmware / wifi_web.c
 * Wi-Fi AP mode + simple HTTP server for live dashboard and WAV download
 */
#include "main.h"
#include "wifi_web.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_http_server.h"
#include "nvs_flash.h"
#include <string.h>

static const char *TAG = "wifi";

static const char *HTML_PAGE =
"<!DOCTYPE html><html><head><title>Cor Sono</title>"
"<meta charset='utf-8'>"
"<style>body{font-family:monospace;background:#111;color:#0f0;margin:20px}"
"h1{color:#0f0}canvas{border:1px solid #0f0}"
".res{font-size:24px;margin:10px}</style></head><body>"
"<h1>Cor Sono — Smart Stethoscope</h1>"
"<canvas id='wf' width='512' height='128'></canvas>"
"<div class='res' id='hr'>HR: -- BPM</div>"
"<div class='res' id='cls'>Class: --</div>"
"<div><button onclick='fetch(\"/rec\")'>Record</button>"
"<button onclick='fetch(\"/mode\")'>Mode</button></div>"
"<div><a href='/wav'>Download WAV</a> | <a href='/csv'>Download CSV</a></div>"
"<script>"
"var ws=new WebSocket('ws://'+location.host+'/ws');"
"ws.onmessage=function(e){var d=JSON.parse(e.data);"
"document.getElementById('hr').textContent='HR: '+d.hr+' BPM';"
"document.getElementById('cls').textContent='Class: '+d.cls+' ('+d.conf+'%)'};"
"</script></body></html>";

static esp_err_t http_root(httpd_req_t *req)
{
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, HTML_PAGE, strlen(HTML_PAGE));
    return ESP_OK;
}

static esp_err_t http_rec(httpd_req_t *req)
{
    on_button_record();
    httpd_resp_send(req, "ok", 2);
    return ESP_OK;
}

static esp_err_t http_mode(httpd_req_t *req)
{
    on_button_mode();
    httpd_resp_send(req, "ok", 2);
    return ESP_OK;
}

static httpd_handle_t server = NULL;

void wifi_web_init(void)
{
    ESP_LOGI(TAG, "init WiFi AP + HTTP server");

    /* WiFi AP mode */
    esp_netif_create_default_ap();
    wifi_config_t cfg = {
        .ap = {
            .ssid = "Cor-Sono",
            .ssid_len = 8,
            .channel = 6,
            .max_connection = 2,
            .authmode = WIFI_AUTH_OPEN,
        },
    };
    esp_wifi_set_mode(WIFI_MODE_AP);
    esp_wifi_set_config(WIFI_IF_AP, &cfg);
    esp_wifi_start();

    /* HTTP server */
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    httpd_start(&server, &config);

    httpd_uri_t root = { .uri="/", .method=HTTP_GET, .handler=http_root };
    httpd_register_uri_handler(server, &root);

    httpd_uri_t rec = { .uri="/rec", .method=HTTP_GET, .handler=http_rec };
    httpd_register_uri_handler(server, &rec);

    httpd_uri_t mode = { .uri="/mode", .method=HTTP_GET, .handler=http_mode };
    httpd_register_uri_handler(server, &mode);

    ESP_LOGI(TAG, "AP: Cor-Sono, dashboard at http://192.168.4.1/");
}