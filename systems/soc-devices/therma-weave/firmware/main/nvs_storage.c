/*
 * Therma Weave — NVS Storage
 * nvs_storage.c — Non-volatile storage for settings persistence
 *
 * SPDX-License-Identifier: MIT
 */

#include "nvs_storage.h"
#include <string.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"

static const char *TAG = "NVS_STORAGE";

void nvs_storage_init(void)
{
    ESP_LOGI(TAG, "NVS storage initialized");
}

void nvs_storage_save_zones(zone_controller_t *zones)
{
    nvs_handle_t handle;
    esp_err_t err;

    err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS: %s", esp_err_to_name(err));
        return;
    }

    for (int z = 0; z < NUM_ZONES; z++) {
        char key[16];

        /* Target temperature */
        snprintf(key, sizeof(key), "z%d_target", z);
        nvs_set_f32(handle, key, zones[z].target_temp);

        /* Enabled state */
        snprintf(key, sizeof(key), "z%d_enable", z);
        nvs_set_u8(handle, key, zones[z].enabled ? 1 : 0);

        /* PID parameters */
        snprintf(key, sizeof(key), "z%d_kp", z);
        nvs_set_f32(handle, key, zones[z].kp);

        snprintf(key, sizeof(key), "z%d_ki", z);
        nvs_set_f32(handle, key, zones[z].ki);

        snprintf(key, sizeof(key), "z%d_kd", z);
        nvs_set_f32(handle, key, zones[z].kd);
    }

    nvs_commit(handle);
    nvs_close(handle);

    ESP_LOGI(TAG, "Zone settings saved to NVS");
}

void nvs_storage_load_zones(zone_controller_t *zones)
{
    nvs_handle_t handle;
    esp_err_t err;

    err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "No stored settings found, using defaults");
        return;
    }

    for (int z = 0; z < NUM_ZONES; z++) {
        char key[16];

        snprintf(key, sizeof(key), "z%d_target", z);
        float target;
        if (nvs_get_f32(handle, key, &target) == ESP_OK) {
            zones[z].target_temp = target;
        }

        snprintf(key, sizeof(key), "z%d_enable", z);
        uint8_t enable;
        if (nvs_get_u8(handle, key, &enable) == ESP_OK) {
            zones[z].enabled = (enable != 0);
        }

        snprintf(key, sizeof(key), "z%d_kp", z);
        float kp;
        if (nvs_get_f32(handle, key, &kp) == ESP_OK) {
            zones[z].kp = kp;
        }

        snprintf(key, sizeof(key), "z%d_ki", z);
        float ki;
        if (nvs_get_f32(handle, key, &ki) == ESP_OK) {
            zones[z].ki = ki;
        }

        snprintf(key, sizeof(key), "z%d_kd", z);
        float kd;
        if (nvs_get_f32(handle, key, &kd) == ESP_OK) {
            zones[z].kd = kd;
        }
    }

    nvs_close(handle);
    ESP_LOGI(TAG, "Zone settings loaded from NVS");
}

float nvs_storage_get_target(uint8_t zone)
{
    nvs_handle_t handle;
    char key[16];
    float target = 0.0f;

    snprintf(key, sizeof(key), "z%d_target", zone);

    if (nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle) == ESP_OK) {
        nvs_get_f32(handle, key, &target);
        nvs_close(handle);
    }

    return target;
}

void nvs_storage_set_target(uint8_t zone, float target)
{
    nvs_handle_t handle;
    char key[16];

    snprintf(key, sizeof(key), "z%d_target", zone);

    if (nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle) == ESP_OK) {
        nvs_set_f32(handle, key, target);
        nvs_commit(handle);
        nvs_close(handle);
    }
}