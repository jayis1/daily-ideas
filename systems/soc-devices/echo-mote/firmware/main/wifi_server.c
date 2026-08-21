/**
 * wifi_server.c — Wi-Fi HTTP REST API server
 *
 * Endpoints:
 *   GET  /api/status         → JSON device status
 *   POST /api/measure        → Trigger measurement
 *   GET  /api/results        → JSON last measurement results
 *   GET  /api/impulse_resp   → Binary raw impulse response
 */

#include "wifi_server.h"
#include <string.h>
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "esp_http_server.h"
#include "cJSON.h"

static const char *TAG = "wifi";

static bool wifi_active = false;
static httpd_handle_t server = NULL;
static acoustic_results_t cached_results;
static uint32_t cached_mode = 0;
static bool has_results = false;

/* ---- HTTP Handlers ---- */

static esp_err_t handler_status(httpd_req_t *req) {
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "device", "EchoMote");
    cJSON_AddStringToObject(root, "status", "idle");
    cJSON_AddNumberToObject(root, "mode", cached_mode);
    cJSON_AddBoolToObject(root, "has_results", has_results);

    char *json = cJSON_PrintUnformatted(root);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, json);
    free(json);
    cJSON_Delete(root);
    return ESP_OK;
}

static esp_err_t handler_results(httpd_req_t *req) {
    if (!has_results) {
        httpd_resp_send_404(req);
        return ESP_OK;
    }

    cJSON *root = cJSON_CreateObject();
    cJSON_AddNumberToObject(root, "mode", cached_mode);
    cJSON_AddNumberToObject(root, "speed_of_sound", cached_results.speed_of_sound);
    cJSON_AddNumberToObject(root, "temperature", cached_results.temperature);
    cJSON_AddNumberToObject(root, "humidity", cached_results.humidity);

    /* RT60 */
    cJSON *rt60 = cJSON_CreateArray();
    for (int i = 0; i < 6; i++) {
        cJSON_AddItemToArray(rt60, cJSON_CreateNumber(cached_results.rt60[i]));
    }
    cJSON_AddItemToObject(root, "rt60", rt60);

    /* C50/C80 */
    cJSON *c50 = cJSON_CreateArray();
    cJSON *c80 = cJSON_CreateArray();
    for (int i = 0; i < 6; i++) {
        cJSON_AddItemToArray(c50, cJSON_CreateNumber(cached_results.c50[i]));
        cJSON_AddItemToArray(c80, cJSON_CreateNumber(cached_results.c80[i]));
    }
    cJSON_AddItemToObject(root, "c50", c50);
    cJSON_AddItemToObject(root, "c80", c80);

    /* Room modes */
    cJSON *modes = cJSON_CreateArray();
    for (int i = 0; i < cached_results.num_modes; i++) {
        cJSON *m = cJSON_CreateObject();
        cJSON_AddNumberToObject(m, "freq", cached_results.room_modes[i].freq);
        cJSON_AddNumberToObject(m, "decay", cached_results.room_modes[i].decay_time);
        cJSON_AddNumberToObject(m, "type", cached_results.room_modes[i].type);
        cJSON_AddItemToArray(modes, m);
    }
    cJSON_AddItemToObject(root, "room_modes", modes);

    /* NC */
    cJSON_AddNumberToObject(root, "nc_rating", cached_results.nc_rating);

    char *json = cJSON_PrintUnformatted(root);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, json);
    free(json);
    cJSON_Delete(root);
    return ESP_OK;
}

static esp_err_t handler_measure(httpd_req_t *req) {
    char buf[64] = {0};
    int ret = httpd_req_recv(req, buf, sizeof(buf) - 1);
    if (ret <= 0) {
        httpd_resp_send_500(req);
        return ESP_OK;
    }

    /* Parse mode from JSON body */
    cJSON *root = cJSON_Parse(buf);
    cJSON *mode_json = cJSON_GetObjectItem(root, "mode");
    if (mode_json && cJSON_IsString(mode_json)) {
        ESP_LOGI(TAG, "HTTP measure request: %s", mode_json->valuestring);
        /* TODO: trigger measurement from app_main state machine */
    }
    cJSON_Delete(root);

    httpd_resp_set_type(req, "application/json");
    httpd_resp_sendstr(req, "{\"status\":\"measuring\"}");
    return ESP_OK;
}

/* ---- Server lifecycle ---- */

static httpd_handle_t start_webserver(void) {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.stack_size = 8192;

    httpd_handle_t handle = NULL;
    if (httpd_start(&handle, &config) == ESP_OK) {
        httpd_uri_t uri_status = { .uri = "/api/status", .method = HTTP_GET,
                                    .handler = handler_status };
        httpd_uri_t uri_results = { .uri = "/api/results", .method = HTTP_GET,
                                    .handler = handler_results };
        httpd_uri_t uri_measure = { .uri = "/api/measure", .method = HTTP_POST,
                                    .handler = handler_measure };
        httpd_register_uri_handler(handle, &uri_status);
        httpd_register_uri_handler(handle, &uri_results);
        httpd_register_uri_handler(handle, &uri_measure);
    }
    return handle;
}

static void stop_webserver(httpd_handle_t handle) {
    httpd_stop(handle);
}

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                                int32_t event_id, void *event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        server = start_webserver();
    }
}

int wifi_server_start(const char *ssid, const char *password) {
    ESP_LOGI(TAG, "Connecting to Wi-Fi: %s", ssid);

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
    strncpy((char *)wifi_cfg.sta.password, password, sizeof(wifi_cfg.sta.password) - 1);

    esp_wifi_set_mode(WIFI_MODE_STA);
    esp_wifi_set_config(WIFI_IF_STA, &wifi_cfg);
    esp_wifi_start();

    wifi_active = true;
    return 0;
}

void wifi_server_stop(void) {
    if (server) {
        stop_webserver(server);
        server = NULL;
    }
    esp_wifi_stop();
    wifi_active = false;
}

bool wifi_server_is_active(void) {
    return wifi_active;
}

int wifi_server_post_results(uint32_t mode, const acoustic_results_t *results) {
    cached_results = *results;
    cached_mode = mode;
    has_results = true;
    return 0;
}