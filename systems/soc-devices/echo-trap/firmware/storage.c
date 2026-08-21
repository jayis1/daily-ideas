/*
 * storage.c — NVS storage for LoRaWAN credentials and config
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "storage.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include <string.h>

static const char *TAG = "storage";

static nvs_handle_t s_nvs;

void storage_init(void)
{
    ESP_LOGI(TAG, "Opening NVS storage");
    esp_err_t err = nvs_open("echotrap", NVS_READWRITE, &s_nvs);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS: %s", esp_err_to_name(err));
    }
}

esp_err_t storage_load_credentials(uint8_t *app_eui, uint8_t *app_key, uint8_t *dev_eui)
{
    size_t len = 8;
    esp_err_t err = nvs_get_blob(s_nvs, "app_eui", app_eui, &len);
    if (err != ESP_OK) return err;
    len = 16;
    err = nvs_get_blob(s_nvs, "app_key", app_key, &len);
    if (err != ESP_OK) return err;
    len = 8;
    err = nvs_get_blob(s_nvs, "dev_eui", dev_eui, &len);
    return err;
}

esp_err_t storage_save_credentials(const uint8_t *app_eui, const uint8_t *app_key,
                                     const uint8_t *dev_eui)
{
    esp_err_t err = nvs_set_blob(s_nvs, "app_eui", app_eui, 8);
    if (err != ESP_OK) return err;
    err = nvs_set_blob(s_nvs, "app_key", app_key, 16);
    if (err != ESP_OK) return err;
    err = nvs_set_blob(s_nvs, "dev_eui", dev_eui, 8);
    if (err != ESP_OK) return err;
    return nvs_commit(s_nvs);
}

void storage_load_lorawan_keys(void)
{
    uint8_t app_eui[8], app_key[16], dev_eui[8];
    if (storage_load_credentials(app_eui, app_key, dev_eui) == ESP_OK) {
        ESP_LOGI(TAG, "LoRaWAN credentials loaded from NVS");
    } else {
        ESP_LOGW(TAG, "No LoRaWAN credentials — provision via BLE");
    }
}