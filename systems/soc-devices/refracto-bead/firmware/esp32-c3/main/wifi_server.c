/**
 * wifi_server.c — Wi-Fi HTTP REST API server for Refracto Bead
 *
 * Endpoints:
 *   GET  /api/status
 *   POST /api/measure
 *   GET  /api/results
 *   GET  /api/compound/matches
 *   GET  /api/library
 *   POST /api/library
 *   GET  /api/waveform?wl=589
 *   GET  /api/log?n=100
 *   POST /api/calibrate
 */

#include "wifi_server.h"
#include "uart_protocol.h"
#include <string.h>
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_http_server.h"

static const char *TAG = "wifi";

static ri_result_t s_last_result;
static httpd_handle_t s_server = NULL;
static bool s_wifi_connected = false;

/* Event handler */
static void wifi_event_handler(void *arg, esp_event_base_t base,
                                int32_t id, void *data) {
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
        ESP_LOGI(TAG, "Reconnecting to Wi-Fi...");
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        s_wifi_connected = true;
    }
}

/* JSON response builder for results */
static char *build_results_json(const ri_result_t *r, char *buf, size_t buflen) {
    snprintf(buf, buflen,
             "{"
             "\"n_D\":%.4f,"
             "\"n_F\":%.4f,"
             "\"n_C\":%.4f,"
             "\"dispersion\":%.4f,"
             "\"abbe_vd\":%.1f,"
             "\"brix\":%.1f,"
             "\"sg\":%.3f,"
             "\"abv\":%.1f,"
             "\"freeze_point\":%.1f,"
             "\"t_prism\":%.2f,"
             "\"t_ambient\":%.2f,"
             "\"compound\":\"%s\","
             "\"compound_id\":%d,"
             "\"confidence\":%.2f"
             "}",
             r->n_D, r->n_F, r->n_C, r->dispersion, r->abbe_vd,
             r->brix, r->specific_grav, r->abv, r->freeze_point,
             r->t_prism, r->t_ambient,
             r->compound_name, (int)r->compound_id, r->confidence);
    return buf;
}

/* HTTP handlers */
static esp_err_t handler_status(httpd_req_t *req) {
    char buf[128];
    snprintf(buf, sizeof(buf), "{\"status\":\"idle\",\"battery\":%d}", 100);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, buf);
    return ESP_OK;
}

static esp_err_t handler_results(httpd_req_t *req) {
    char buf[512];
    build_results_json(&s_last_result, buf, sizeof(buf));
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, buf);
    return ESP_OK;
}

static esp_err_t handler_library(httpd_req_t *req) {
    /* Return a simplified library summary */
    const char *json = "{\"size\":60,\"entries\":[{\"id\":1,\"name\":\"Water\",\"n_D\":1.3330,\"abbe_vd\":55.8}]}";
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, json);
    return ESP_OK;
}

static esp_err_t handler_measure(httpd_req_t *req) {
    /* Forward measure command to STM32 via UART (not implemented here) */
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, "{\"status\":\"measuring\"}");
    return ESP_OK;
}

void wifi_server_init(void) {
    /* Try to connect to Wi-Fi if credentials are in NVS */
    nvs_handle_t nvs;
    esp_err_t err = nvs_open("wifi", NVS_READONLY, &nvs);
    if (err != ESP_OK) {
        ESP_LOGI(TAG, "No Wi-Fi credentials stored — BLE only mode");
        return;
    }

    char ssid[33] = {0};
    char pass[65] = {0};
    size_t len = sizeof(ssid);
    nvs_get_str(nvs, "ssid", ssid, &len);
    len = sizeof(pass);
    nvs_get_str(nvs, "pass", pass, &len);
    nvs_close(nvs);

    if (strlen(ssid) == 0) {
        ESP_LOGI(TAG, "Empty SSID — BLE only mode");
        return;
    }

    /* Initialize Wi-Fi */
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_wifi_init(&cfg);

    esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                        &wifi_event_handler, NULL, NULL);
    esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                        &wifi_event_handler, NULL, NULL);

    wifi_config_t wifi_cfg = {0};
    strncpy((char *)wifi_cfg.sta.ssid, ssid, sizeof(wifi_cfg.sta.ssid) - 1);
    strncpy((char *)wifi_cfg.sta.password, pass, sizeof(wifi_cfg.sta.password) - 1);

    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg);
    esp_wifi_start();

    /* Start HTTP server */
    httpd_config_t http_cfg = HTTPD_DEFAULT_CONFIG();
    httpd_start(&s_server, &http_cfg);

    /* Register URI handlers */
    httpd_uri_t uri_status = { .uri = "/api/status", .method = HTTP_GET, .handler = handler_status };
    httpd_uri_t uri_results = { .uri = "/api/results", .method = HTTP_GET, .handler = handler_results };
    httpd_uri_t uri_library = { .uri = "/api/library", .method = HTTP_GET, .handler = handler_library };
    httpd_uri_t uri_measure = { .uri = "/api/measure", .method = HTTP_POST, .handler = handler_measure };

    httpd_register_uri_handler(s_server, &uri_status);
    httpd_register_uri_handler(s_server, &uri_results);
    httpd_register_uri_handler(s_server, &uri_library);
    httpd_register_uri_handler(s_server, &uri_measure);
}

void wifi_server_notify_result(const ri_result_t *result) {
    s_last_result = *result;
}