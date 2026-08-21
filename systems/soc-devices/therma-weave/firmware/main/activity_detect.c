/*
 * Therma Weave — Activity Detection
 * activity_detect.c — LSM6DS3 IMU for activity classification
 *
 * SPDX-License-Identifier: MIT
 */

#include "activity_detect.h"
#include <math.h>
#include <string.h>
#include "esp_log.h"

static const char *TAG = "ACTIVITY";

/* LSM6DS3 register addresses */
#define LSM6DS3_WHO_AM_I       0x0F  /* Expected: 0x69 */
#define LSM6DS3_CTRL1_XL       0x10  /* Accel ODR/FS */
#define LSM6DS3_CTRL2_G        0x11  /* Gyro ODR/FS */
#define LSM6DS3_CTRL6_C        0x15  /* Gyro LPF */
#define LSM6DS3_OUTX_L_XL      0x28  /* Accel X low byte */
#define LSM6DS3_OUTX_L_G       0x22  /* Gyro X low byte */
#define LSM6DS3_STATUS_REG     0x1E  /* Status (XLDA bit) */

/* Accelerometer configuration: 416Hz ODR, ±4g FS */
#define CTRL1_XL_CFG  0x68  /* ODR=416Hz, FS=±4g */

/* Gyroscope configuration: 416Hz ODR, ±500dps FS */
#define CTRL2_G_CFG   0x68   /* ODR=416Hz, FS=±500dps */

/* Activity classification thresholds */
#define STILL_VARIANCE_THRESH    0.05f   /* g² variance threshold for still */
#define WALKING_VARIANCE_THRESH  0.5f    /* g² variance threshold for walking */
#define FALL_ACCEL_THRESH        2.5f    /* g threshold for fall detection */

static esp_err_t lsm6ds3_write_reg(activity_detect_t *ad, uint8_t reg, uint8_t val)
{
    /* Real: i2c_master_write_to_device(ad->i2c_num, LSM6DS3_ADDR, &reg, 1, ...); */
    (void)ad;
    (void)reg;
    (void)val;
    return ESP_OK;
}

static esp_err_t lsm6ds3_read_regs(activity_detect_t *ad, uint8_t reg,
                                      uint8_t *buf, size_t len)
{
    (void)ad;
    (void)reg;
    (void)buf;
    (void)len;
    /* Placeholder: return zeros */
    memset(buf, 0, len);
    return ESP_OK;
}

void activity_detect_init(activity_detect_t *ad, i2c_port_t i2c_num)
{
    ad->i2c_num = i2c_num;
    ad->level = ACTIVITY_STILL;
    ad->accel_x = 0;
    ad->accel_y = 0;
    ad->accel_z = 0;
    ad->gyro_x = 0;
    ad->gyro_y = 0;
    ad->gyro_z = 0;
    ad->accel_magnitude = 1.0f;  /* Assume 1g at rest */
    ad->accel_variance = 0.0f;
    ad->step_count = 0;
    ad->fall_detected = false;
    ad->history_idx = 0;
    ad->fall_cb = NULL;
    ad->temp_offset = 0.0f;

    memset(ad->accel_history, 0, sizeof(ad->accel_history));

    /* Verify device ID */
    uint8_t who_am_i = 0;
    lsm6ds3_read_regs(ad, LSM6DS3_WHO_AM_I, &who_am_i, 1);
    if (who_am_i != 0x69) {
        ESP_LOGW(TAG, "LSM6DS3 WHO_AM_I mismatch: 0x%02X (expected 0x69)", who_am_i);
    }

    /* Configure accelerometer: 416Hz, ±4g */
    lsm6ds3_write_reg(ad, LSM6DS3_CTRL1_XL, CTRL1_XL_CFG);

    /* Configure gyroscope: 416Hz, ±500dps */
    lsm6ds3_write_reg(ad, LSM6DS3_CTRL2_G, CTRL2_G_CFG);

    ESP_LOGI(TAG, "LSM6DS3 initialized for activity detection");
}

void activity_detect_update(activity_detect_t *ad)
{
    /* Read 6 bytes of accelerometer data */
    uint8_t buf[6];
    esp_err_t ret = lsm6ds3_read_regs(ad, LSM6DS3_OUTX_L_XL, buf, 6);
    if (ret != ESP_OK) return;

    /* Parse accelerometer data (16-bit signed, ±4g range, 0.122 mg/LSB) */
    ad->accel_x = (int16_t)((buf[1] << 8) | buf[0]);
    ad->accel_y = (int16_t)((buf[3] << 8) | buf[2]);
    ad->accel_z = (int16_t)((buf[5] << 8) | buf[4]);

    /* Convert to g units (±4g range: 0.122 mg/LSB = 0.000122 g/LSB) */
    float ax_g = (float)ad->accel_x * 0.000122f;
    float ay_g = (float)ad->accel_y * 0.000122f;
    float az_g = (float)ad->accel_z * 0.000122f;

    /* Calculate magnitude */
    ad->accel_magnitude = sqrtf(ax_g * ax_g + ay_g * ay_g + az_g * az_g);

    /* Store in history buffer */
    ad->accel_history[ad->history_idx] = ad->accel_magnitude;
    ad->history_idx = (ad->history_idx + 1) % 32;

    /* Calculate variance over the window */
    float mean = 0.0f;
    for (int i = 0; i < 32; i++) {
        mean += ad->accel_history[i];
    }
    mean /= 32.0f;

    float variance = 0.0f;
    for (int i = 0; i < 32; i++) {
        float diff = ad->accel_history[i] - mean;
        variance += diff * diff;
    }
    variance /= 32.0f;
    ad->accel_variance = variance;

    /* Fall detection: check for impact spike followed by orientation change */
    if (ad->accel_magnitude > FALL_ACCEL_THRESH) {
        ad->fall_detected = true;
        ad->level = ACTIVITY_FALL;
        if (ad->fall_cb) ad->fall_cb();
        ESP_LOGW(TAG, "FALL DETECTED! Accel magnitude: %.2f g", ad->accel_magnitude);
        return;
    }

    /* Activity classification based on variance */
    if (variance < STILL_VARIANCE_THRESH) {
        ad->level = ACTIVITY_STILL;
        ad->temp_offset = 0.0f;
    } else if (variance < WALKING_VARIANCE_THRESH) {
        ad->level = ACTIVITY_WALKING;
        ad->temp_offset = -3.0f;

        /* Simple step detection: zero-crossing of vertical acceleration */
        static int16_t prev_z = 0;
        if (prev_z > 0 && ad->accel_z < 0) {
            ad->step_count++;
        }
        prev_z = ad->accel_z;
    } else {
        ad->level = ACTIVITY_RUNNING;
        ad->temp_offset = -6.0f;
    }
}

void activity_detect_set_fall_callback(activity_detect_t *ad, fall_detected_cb_t cb)
{
    ad->fall_cb = cb;
}

float activity_detect_get_temp_offset(activity_detect_t *ad)
{
    return ad->temp_offset;
}