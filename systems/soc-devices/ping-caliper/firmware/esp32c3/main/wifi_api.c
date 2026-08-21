/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/wifi_api.c — Wi-Fi AP mode for direct phone connection + OTA update
 *
 * The ESP32-C3 hosts a small open AP "PingCaliper-XXXX" for phone-to-device
 * connection when no Wi-Fi network is available. The phone app connects to
 * the AP to fetch logs and trigger OTA updates via a minimal HTTP server.
 * In station mode (if configured) it joins a known network for OTA/cloud.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "wifi_api.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_http_client.h"
#include <string.h>

static const char *TAG = "wifi_api";
static bool g_ap_started = false;
static bool g_sta_connected = false;

static void event_handler(void *arg, esp_event_base_t base,
                          int32_t id, void *data)
{
    (void)arg;
    if (base == WIFI_EVENT && id == WIFI_EVENT_AP_START) {
        g_ap_started = true;
        ESP_LOGI(TAG, "AP started");
    } else if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        g_sta_connected = false;
        esp_wifi_connect();
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        g_sta_connected = true;
        ESP_LOGI(TAG, "STA got IP");
    }
}

void wifi_api_init(void)
{
    esp_netif_init();
    esp_event_loop_create_default();
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                         event_handler, NULL, NULL);
    esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                         event_handler, NULL, NULL);

    /* Start in AP mode by default (direct phone connection) */
    wifi_config_t ap_cfg = {
        .ap = {
            .ssid = "PingCaliper",
            .ssid_len = strlen("PingCaliper"),
            .channel = 6,
            .password = "",
            .max_connection = 4,
            .authmode = WIFI_AUTH_OPEN,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_cfg));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(TAG, "Wi-Fi AP 'PingCaliper' up on channel 6");
}

bool wifi_is_connected(void)
{
    return g_sta_connected;
}

/* ---- OTA firmware update ---- */
static void ota_task(void *url)
{
    char *u = (char *)url;
    esp_http_client_config_t http_cfg = {
        .url = u,
        .timeout_ms = 10000,
        .buffer_size = 4096,
    };

    esp_ota_handle_t handle = 0;
    const esp_partition_t *part = esp_ota_get_next_update_partition(NULL);
    if (!part) { ESP_LOGE(TAG, "No OTA partition"); free(u); vTaskDelete(NULL); return; }

    ESP_ERROR_CHECK(esp_ota_begin(part, OTA_SIZE_UNKNOWN, &handle));

    esp_http_client_handle_t client = esp_http_client_init(&http_cfg);
    esp_err_t err = esp_http_client_open(client, 0);
    if (err != ESP_OK) { ESP_LOGE(TAG, "HTTP open failed"); free(u); vTaskDelete(NULL); return; }

    char buf[4096];
    int total = 0;
    int rd;
    while ((rd = esp_http_client_read(client, buf, sizeof(buf))) > 0) {
        esp_ota_write(handle, buf, rd);
        total += rd;
    }
    esp_http_client_close(client);
    esp_http_client_cleanup(client);

    ESP_ERROR_CHECK(esp_ota_end(handle));
    ESP_ERROR_CHECK(esp_ota_set_boot_partition(part));
    ESP_LOGI(TAG, "OTA done: %d bytes written. Rebooting.", total);
    free(u);
    esp_restart();
}

void wifi_ota_start(const char *url)
{
    if (!url) return;
    char *u = strdup(url);
    xTaskCreate(ota_task, "ota", 8192, u, 5, NULL);
}