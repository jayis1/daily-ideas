/*
 * Spectra Charm — ESP32-C3 WiFi REST API Server
 *
 * wifi_api.c — HTTP server with JSON endpoints
 */

#include "wifi_api.h"
#include <string.h>
#include "esp_log.h"
#include "esp_http_server.h"
#include "cJSON.h"
#include "uart_comm.h"

static const char *TAG = "WiFiAPI";
static httpd_handle_t server = NULL;

/* Last scan result cache */
static float last_spectrum[128] = {0};
static char last_compound[32] = "None";
static float last_concentration = 0.0f;
static float last_confidence = 0.0f;
static uint8_t last_battery = 100;

/* ---- POST /api/v1/scan — Trigger new scan ---- */
static esp_err_t scan_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "Scan request received");

    /* Parse optional JSON body for scan type */
    char buf[64] = {0};
    int ret = httpd_req_recv(req, buf, sizeof(buf) - 1);
    if (ret > 0) {
        cJSON *root = cJSON_Parse(buf);
        if (root) {
            cJSON *type = cJSON_GetObjectItem(root, "type");
            if (type && cJSON_IsNumber(type)) {
                UART_SendScanRequest((uint8_t)type->valueint);
            }
            cJSON_Delete(root);
        }
    } else {
        UART_SendScanRequest(2); /* Default: sample scan */
    }

    const char *resp = "{\"status\":\"scanning\"}";
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, resp, strlen(resp));
    return ESP_OK;
}

/* ---- GET /api/v1/spectrum — Get last spectrum ---- */
static esp_err_t spectrum_handler(httpd_req_t *req)
{
    cJSON *root = cJSON_CreateObject();
    cJSON_AddNumberToObject(root, "points", 128);
    cJSON_AddNumberToObject(root, "wl_start", 340.0);
    cJSON_AddNumberToObject(root, "wl_end", 700.0);

    cJSON *arr = cJSON_CreateArray();
    for (int i = 0; i < 128; i++) {
        cJSON_AddItemToArray(arr, cJSON_CreateNumber(last_spectrum[i]));
    }
    cJSON_AddItemToObject(root, "absorbance", arr);

    char *json = cJSON_PrintUnformatted(root);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, json, strlen(json));
    cJSON_free(json);
    cJSON_Delete(root);
    return ESP_OK;
}

/* ---- GET /api/v1/match — Get compound match ---- */
static esp_err_t match_handler(httpd_req_t *req)
{
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "compound", last_compound);
    cJSON_AddNumberToObject(root, "confidence", last_confidence);
    cJSON_AddNumberToObject(root, "concentration_mol_L", last_concentration);

    char *json = cJSON_PrintUnformatted(root);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, json, strlen(json));
    cJSON_free(json);
    cJSON_Delete(root);
    return ESP_OK;
}

/* ---- GET /api/v1/battery — Battery status ---- */
static esp_err_t battery_handler(httpd_req_t *req)
{
    cJSON *root = cJSON_CreateObject();
    cJSON_AddNumberToObject(root, "percent", last_battery);
    cJSON_AddStringToObject(root, "status", last_battery < 100 ? "charging" : "full");

    char *json = cJSON_PrintUnformatted(root);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, json, strlen(json));
    cJSON_free(json);
    cJSON_Delete(root);
    return ESP_OK;
}

/* ---- GET /api/v1/config — Device config ---- */
static esp_err_t config_handler(httpd_req_t *req)
{
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "name", "Spectra Charm");
    cJSON_AddStringToObject(root, "version", "1.0.0");
    cJSON_AddNumberToObject(root, "wavelength_start_nm", 340);
    cJSON_AddNumberToObject(root, "wavelength_end_nm", 700);
    cJSON_AddNumberToObject(root, "points", 128);
    cJSON_AddNumberToObject(root, "path_length_cm", 1.0);

    char *json = cJSON_PrintUnformatted(root);
    httpd_resp_set_type(req, "application/json");
    httpd_resp_send(req, json, strlen(json));
    cJSON_free(json);
    cJSON_Delete(root);
    return ESP_OK;
}

/* ---- URI table ---- */
static const httpd_uri_t uris[] = {
    { .uri = "/api/v1/scan",     .method = HTTP_POST, .handler = scan_handler,     .user_ctx = NULL },
    { .uri = "/api/v1/spectrum",  .method = HTTP_GET,  .handler = spectrum_handler, .user_ctx = NULL },
    { .uri = "/api/v1/match",    .method = HTTP_GET,  .handler = match_handler,    .user_ctx = NULL },
    { .uri = "/api/v1/battery",  .method = HTTP_GET,  .handler = battery_handler,  .user_ctx = NULL },
    { .uri = "/api/v1/config",   .method = HTTP_GET,  .handler = config_handler,   .user_ctx = NULL },
};

void WiFi_API_Start(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;
    config.max_uri_handlers = 8;

    if (httpd_start(&server, &config) == ESP_OK) {
        for (int i = 0; i < sizeof(uris) / sizeof(uris[0]); i++) {
            httpd_register_uri_handler(server, &uris[i]);
        }
        ESP_LOGI(TAG, "HTTP server started on port 80");
    } else {
        ESP_LOGE(TAG, "Failed to start HTTP server");
    }
}

void WiFi_API_UpdateSpectrum(const float *data, int len)
{
    if (len > 128) len = 128;
    memcpy(last_spectrum, data, len * sizeof(float));
}

void WiFi_API_UpdateMatch(const char *compound, float confidence, float concentration)
{
    strncpy(last_compound, compound, sizeof(last_compound) - 1);
    last_confidence = confidence;
    last_concentration = concentration;
}