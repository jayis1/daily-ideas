/*
 * Therma Weave — Activity Detection
 * activity_detect.h — LSM6DS3 IMU for activity classification
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef ACTIVITY_DETECT_H
#define ACTIVITY_DETECT_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/i2c.h"

#define LSM6DS3_ADDR       0x6A

/* Activity levels */
typedef enum {
    ACTIVITY_STILL   = 0,
    ACTIVITY_WALKING = 1,
    ACTIVITY_RUNNING = 2,
    ACTIVITY_FALL    = 3,
} activity_level_t;

/* Fall detection callback */
typedef void (*fall_detected_cb_t)(void);

typedef struct {
    i2c_port_t i2c_num;
    activity_level_t level;

    /* Accelerometer data (mg) */
    int16_t accel_x;
    int16_t accel_y;
    int16_t accel_z;

    /* Gyroscope data (dps) */
    int16_t gyro_x;
    int16_t gyro_y;
    int16_t gyro_z;

    /* Activity classification */
    float accel_magnitude;       /* RMS acceleration magnitude */
    float accel_variance;         /* Variance over window */
    int   step_count;             /* Total step count */
    bool  fall_detected;          /* Fall detection flag */

    /* Classification window */
    float accel_history[32];      /* Last 32 acceleration magnitude samples */
    int   history_idx;

    /* Fall detection callback */
    fall_detected_cb_t fall_cb;

    /* Activity offset for heating adjustment (°C) */
    float temp_offset;
} activity_detect_t;

/**
 * Initialize LSM6DS3 IMU and configure for activity detection.
 */
void activity_detect_init(activity_detect_t *ad, i2c_port_t i2c_num);

/**
 * Read IMU data and update activity classification.
 * Call at 50 Hz.
 */
void activity_detect_update(activity_detect_t *ad);

/**
 * Register a callback for fall detection events.
 */
void activity_detect_set_fall_callback(activity_detect_t *ad, fall_detected_cb_t cb);

/**
 * Get the current recommended temperature offset based on activity.
 * Returns: 0.0 (still), -3.0 (walking), -6.0 (running)
 */
float activity_detect_get_temp_offset(activity_detect_t *ad);

#endif /* ACTIVITY_DETECT_H */