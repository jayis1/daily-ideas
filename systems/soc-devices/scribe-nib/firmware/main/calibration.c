/*
 * calibration.c — User handwriting profile calibration for Scribe Nib
 *
 * Stores up to 4 user profiles in NVS, each containing stroke
 * scaling factors and timing adjustments for personalized recognition.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "calibration.h"
#include <string.h>
#include <math.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"

static const char *TAG = "calibration";

#define NVS_NAMESPACE   "scribenib"
#define MAX_PROFILES    4
#define PROFILE_KEY_LEN 8

/* Calibration profile data */
typedef struct {
    float accel_z_gravity;   /* Z-axis gravity reference when pen is upright */
    float stroke_scale;      /* Scaling factor for trajectory normalization */
    float pen_down_thresh;   /* Pen-down Z-acceleration threshold */
    float pen_up_thresh;     /* Pen-up Z-acceleration threshold */
    float stroke_speed;      /* Average writing speed (for ODR adjustment) */
    uint8_t flags;           /* Bit flags: bit0=caps_preferred, bit1=letter_mode */
    uint32_t sample_count;   /* Number of calibration samples collected */
    uint32_t crc;            /* Simple CRC for integrity check */
} calibration_profile_t;

static calibration_profile_t profiles[MAX_PROFILES];
static uint8_t active_profile = 0;

/* ---- Helpers ---- */

static uint32_t simple_crc(const uint8_t *data, size_t len)
{
    uint32_t crc = 0xDEADBEEF;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        crc = (crc << 1) | (crc >> 31);
    }
    return crc;
}

/* ---- Public API ---- */

esp_err_t calibration_load_profile(uint8_t profile_id)
{
    if (profile_id >= MAX_PROFILES) return ESP_ERR_INVALID_ARG;

    nvs_handle_t handle;
    char key[PROFILE_KEY_LEN + 1];
    snprintf(key, sizeof(key), "prof%d", profile_id);

    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &handle);
    if (err != ESP_OK) {
        /* NVS not yet written — use defaults */
        ESP_LOGW(TAG, "No calibration data for profile %d, using defaults", profile_id);
        profiles[profile_id] = (calibration_profile_t){
            .accel_z_gravity = 9.81f,
            .stroke_scale = 1.0f,
            .pen_down_thresh = 3.0f,
            .pen_up_thresh = 2.0f,
            .stroke_speed = 1.0f,
            .flags = 0,
            .sample_count = 0,
            .crc = 0,
        };
        active_profile = profile_id;
        return ESP_OK;
    }

    size_t required_size = sizeof(calibration_profile_t);
    err = nvs_get_blob(handle, key, &profiles[profile_id], &required_size);

    if (err == ESP_OK) {
        /* Verify CRC */
        uint32_t stored_crc = profiles[profile_id].crc;
        profiles[profile_id].crc = 0;
        uint32_t computed_crc = simple_crc(
            (const uint8_t *)&profiles[profile_id],
            sizeof(calibration_profile_t) - sizeof(uint32_t));

        if (computed_crc != stored_crc) {
            ESP_LOGW(TAG, "Profile %d CRC mismatch (stored=0x%08X computed=0x%08X), using defaults",
                     profile_id, stored_crc, computed_crc);
            profiles[profile_id] = (calibration_profile_t){
                .accel_z_gravity = 9.81f,
                .stroke_scale = 1.0f,
                .pen_down_thresh = 3.0f,
                .pen_up_thresh = 2.0f,
                .stroke_speed = 1.0f,
                .flags = 0,
                .sample_count = 0,
                .crc = 0,
            };
        }
    }

    nvs_close(handle);
    active_profile = profile_id;

    ESP_LOGI(TAG, "Profile %d loaded: gravity=%.2f scale=%.2f thresh=%.2f/%.2f",
             profile_id,
             profiles[profile_id].accel_z_gravity,
             profiles[profile_id].stroke_scale,
             profiles[profile_id].pen_down_thresh,
             profiles[profile_id].pen_up_thresh);

    return ESP_OK;
}

esp_err_t calibration_save_profile(uint8_t profile_id)
{
    if (profile_id >= MAX_PROFILES) return ESP_ERR_INVALID_ARG;

    /* Compute CRC before saving */
    profiles[profile_id].crc = 0;
    profiles[profile_id].crc = simple_crc(
        (const uint8_t *)&profiles[profile_id],
        sizeof(calibration_profile_t) - sizeof(uint32_t));

    nvs_handle_t handle;
    char key[PROFILE_KEY_LEN + 1];
    snprintf(key, sizeof(key), "prof%d", profile_id);

    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;

    err = nvs_set_blob(handle, key, &profiles[profile_id], sizeof(calibration_profile_t));
    if (err == ESP_OK) {
        err = nvs_commit(handle);
        ESP_LOGI(TAG, "Profile %d saved (CRC=0x%08X)", profile_id, profiles[profile_id].crc);
    }

    nvs_close(handle);
    return err;
}

esp_err_t calibration_update_gravity(float z_accel)
{
    /* Running average of Z-axis gravity from stationary samples */
    calibration_profile_t *p = &profiles[active_profile];
    float alpha = 0.1f;
    p->accel_z_gravity = p->accel_z_gravity * (1.0f - alpha) + z_accel * alpha;
    p->sample_count++;

    return ESP_OK;
}

float calibration_get_gravity(void)
{
    return profiles[active_profile].accel_z_gravity;
}

float calibration_get_stroke_scale(void)
{
    return profiles[active_profile].stroke_scale;
}

void calibration_set_stroke_scale(float scale)
{
    profiles[active_profile].stroke_scale = scale;
}

uint8_t calibration_get_active_profile(void)
{
    return active_profile;
}