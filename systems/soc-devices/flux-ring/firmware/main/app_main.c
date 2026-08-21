/*
 * Flux Ring — app_main.c
 * Main entry point for the wearable magnetic field explorer.
 * nRF52840, Zephyr RTOS based.
 *
 * SPDX-License-Identifier: MIT
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/pm/device.h>
#include <zephyr/logging/log.h>
#include <stdio.h>
#include <string.h>

#include "mag_sensor.h"
#include "accel_sensor.h"
#include "baro_sensor.h"
#include "field_engine.h"
#include "haptic_feedback.h"
#include "led_feedback.h"
#include "oled_display.h"
#include "ble_service.h"
#include "data_logger.h"
#include "power_manager.h"
#include "touch_input.h"
#include "compass.h"

LOG_MODULE_REGISTER(app_main, LOG_LEVEL_INF);

/* Operating modes */
typedef enum {
    MODE_MONITOR = 0,   /* 10Hz, BLE adv only, low power */
    MODE_EXPLORE  = 1,  /* 100Hz, BLE connected, full feedback */
    MODE_MAPPING  = 2,  /* 200Hz, BLE streaming, max data rate */
    MODE_COMPASS  = 3,  /* 25Hz, BLE adv, compass focus */
    MODE_COUNT
} mode_t;

/* Sample rates per mode (Hz) */
static const int mode_sample_rate_hz[MODE_COUNT] = { 10, 100, 200, 25 };

/* Current operating mode */
static mode_t current_mode = MODE_EXPLORE;
static K_MUTEX_DEFINE(mode_mutex);

/* Calibration state */
static bool calibration_done = false;
static mag_calibration_t mag_cal = {0};

/* I2C bus spec */
#define I2C_NODE DT_NODELABEL(i2c0)
static const struct device *i2c_dev;

/* Thread stacks */
#define SENSOR_STACK_SIZE 2048
#define BLE_STACK_SIZE    2048
#define DISPLAY_STACK_SIZE 1024

static K_THREAD_STACK_DEFINE(sensor_stack, SENSOR_STACK_SIZE);
static K_THREAD_STACK_DEFINE(ble_stack, BLE_STACK_SIZE);
static K_THREAD_STACK_DEFINE(display_stack, DISPLAY_STACK_SIZE);

static struct k_thread sensor_thread_data;
static struct k_thread ble_thread_data;
static struct k_thread display_thread_data;

/* Shared sensor data (protected by mutex) */
typedef struct {
    field_vector_t field;        /* Tilt-compensated field (Gauss) */
    float magnitude;             /* |field| in Gauss */
    compass_heading_t heading;   /* 0-359 degrees */
    pole_t dominant_pole;        /* N, S, or none */
    accel_data_t accel;          /* Raw accelerometer */
    baro_data_t baro;            /* Pressure + altitude */
    uint8_t battery_pct;         /* Battery level 0-100 */
    uint32_t timestamp_ms;       /* System uptime at sample */
} sensor_snapshot_t;

static sensor_snapshot_t latest_snapshot;
static K_MUTEX_DEFINE(snapshot_mutex);

/* Semaphore: sensor thread signals display/BLE threads */
static struct k_sem snapshot_sem;

/*---------------------------------------------------------------------------*/
/* Mode cycling via touch input callback                                      */
/*---------------------------------------------------------------------------*/
static void touch_mode_cb(void)
{
    k_mutex_lock(&mode_mutex, K_FOREVER);
    current_mode = (current_mode + 1) % MODE_COUNT;
    mode_t m = current_mode;
    k_mutex_unlock(&mode_mutex);

    LOG_INF("Mode changed to %d (sample rate %d Hz)", m, mode_sample_rate_hz[m]);

    /* Brief haptic pulse to acknowledge mode change */
    haptic_pulse(50); /* 50ms pulse */
}

static void touch_double_tap_cb(void)
{
    /* Double-tap toggles mapping mode */
    k_mutex_lock(&mode_mutex, K_FOREVER);
    if (current_mode == MODE_MAPPING) {
        current_mode = MODE_EXPLORE;
    } else {
        current_mode = MODE_MAPPING;
    }
    mode_t m = current_mode;
    k_mutex_unlock(&mode_mutex);

    LOG_INF("Double-tap: mode -> %d", m);

    /* Two quick pulses for mapping mode */
    if (current_mode == MODE_MAPPING) {
        haptic_pulse(30);
        k_msleep(80);
        haptic_pulse(30);
    }
}

/*---------------------------------------------------------------------------*/
/* Sensor thread — reads sensors, computes field, updates snapshot            */
/*---------------------------------------------------------------------------*/
static void sensor_thread_fn(void *arg1, void *arg2, void *arg3)
{
    (void)arg1; (void)arg2; (void)arg3;

    int64_t next_wake = k_uptime_get();
    mag_data_t mag_raw;
    accel_data_t accel_raw;
    baro_data_t baro_raw;

    /* Initial calibration */
    if (!calibration_done) {
        LOG_INF("Starting figure-8 calibration — rotate ring for 10s...");
        oled_display_calibrating();

        mag_calibration_t cal;
        int rc = mag_sensor_calibrate(&cal, 10000); /* 10 second figure-8 */
        if (rc == 0) {
            mag_cal = cal;
            calibration_done = true;
            LOG_INF("Calibration complete: offset=(%.2f, %.2f, %.2f)",
                    cal.offset_x, cal.offset_y, cal.offset_z);
            oled_display_cal_ok();
        } else {
            LOG_WRN("Calibration failed, using defaults");
            /* Use identity calibration (SET/RESET will still help) */
            mag_cal.offset_x = 0;
            mag_cal.offset_y = 0;
            mag_cal.offset_z = 0;
            mag_cal.scale_x = 1.0f;
            mag_cal.scale_y = 1.0f;
            mag_cal.scale_z = 1.0f;
            calibration_done = true;
        }
        k_msleep(500);
    }

    /* Periodic SET/RESET for offset cancellation (every 10s) */
    int64_t last_set_reset = k_uptime_get();

    while (1) {
        k_mutex_lock(&mode_mutex, K_FOREVER);
        mode_t mode = current_mode;
        int rate_hz = mode_sample_rate_hz[mode];
        k_mutex_unlock(&mode_mutex);

        int64_t period_us = 1000000LL / rate_hz;

        /* Periodic SET/RESET */
        if (k_uptime_get() - last_set_reset > 10000) {
            mag_sensor_set_reset();
            last_set_reset = k_uptime_get();
        }

        /* Read all sensors */
        int rc1 = mag_sensor_read(&mag_raw);
        int rc2 = accel_sensor_read(&accel_raw);
        int rc3 = baro_sensor_read(&baro_raw);

        if (rc1 != 0 || rc2 != 0) {
            LOG_WRN("Sensor read failed: mag=%d accel=%d", rc1, rc2);
            next_wake += period_us;
            k_sleep(K_TIMEOUT_ABS_US(next_wake));
            continue;
        }

        /* Apply calibration to raw magnetometer data */
        mag_data_t mag_calibrated;
        mag_calibrated.x = (mag_raw.x - mag_cal.offset_x) * mag_cal.scale_x;
        mag_calibrated.y = (mag_raw.y - mag_cal.offset_y) * mag_cal.scale_y;
        mag_calibrated.z = (mag_raw.z - mag_cal.offset_z) * mag_cal.scale_z;

        /* Tilt compensation */
        field_vector_t field = field_engine_compensate(&mag_calibrated, &accel_raw);

        /* Magnitude */
        float magnitude = field_engine_magnitude(&field);

        /* Compass heading */
        compass_heading_t heading = compass_compute(&field, &accel_raw);

        /* Dominant pole detection */
        pole_t pole = field_engine_dominant_pole(&field);

        /* Update snapshot */
        k_mutex_lock(&snapshot_mutex, K_FOREVER);
        latest_snapshot.field = field;
        latest_snapshot.magnitude = magnitude;
        latest_snapshot.heading = heading;
        latest_snapshot.dominant_pole = pole;
        latest_snapshot.accel = accel_raw;
        latest_snapshot.baro = (rc3 == 0) ? baro_raw : latest_snapshot.baro;
        latest_snapshot.battery_pct = power_manager_battery_pct();
        latest_snapshot.timestamp_ms = (uint32_t)k_uptime_get_32();
        k_mutex_unlock(&snapshot_mutex);

        /* Signal display and BLE threads */
        k_sem_give(&snapshot_sem);

        /* Feedback (only in explore/mapping/compass modes) */
        if (mode != MODE_MONITOR) {
            led_feedback_set_field(magnitude, pole);
        }

        if (mode == MODE_EXPLORE || mode == MODE_MAPPING) {
            haptic_feedback_set_intensity(magnitude, pole);
        } else {
            haptic_feedback_off();
        }

        /* Log to flash */
        if (mode == MODE_MONITOR || mode == MODE_EXPLORE) {
            data_logger_append(&field, &accel_raw, heading);
        }

        /* Sleep until next sample */
        next_wake += period_us;
        int64_t now = k_uptime_get();
        if (next_wake > now) {
            k_sleep(K_TIMEOUT_ABS_US(next_wake));
        } else {
            /* We're behind — reset to avoid runaway */
            next_wake = now + period_us;
        }
    }
}

/*---------------------------------------------------------------------------*/
/* BLE thread — handles BLE advertising, connections, and streaming           */
/*---------------------------------------------------------------------------*/
static void ble_thread_fn(void *arg1, void *arg2, void *arg3)
{
    (void)arg1; (void)arg2; (void)arg3;

    ble_service_init();

    while (1) {
        /* Wait for new sensor data */
        k_sem_take(&snapshot_sem, K_MSEC(1000));

        k_mutex_lock(&snapshot_mutex, K_FOREVER);
        sensor_snapshot_t snap = latest_snapshot;
        k_mutex_unlock(&snapshot_mutex);

        k_mutex_lock(&mode_mutex, K_FOREVER);
        mode_t mode = current_mode;
        k_mutex_unlock(&mode_mutex);

        /* Update BLE characteristics */
        ble_service_update_field(snap.field.x, snap.field.y, snap.field.z,
                                 snap.magnitude, snap.heading,
                                 snap.dominant_pole, snap.battery_pct);

        /* Stream in mapping mode */
        if (mode == MODE_MAPPING && ble_is_connected()) {
            ble_stream_sample(&snap.field, &snap.accel, &snap.baro,
                              snap.heading, snap.timestamp_ms);
        }

        /* Update advertising data in monitor/compass modes */
        if (mode == MODE_MONITOR || mode == MODE_COMPASS) {
            ble_service_update_advertising(snap.magnitude, snap.heading,
                                           snap.dominant_pole, mode);
        }

        k_msleep(1); /* Yield */
    }
}

/*---------------------------------------------------------------------------*/
/* Display thread — updates OLED                                             */
/*---------------------------------------------------------------------------*/
static void display_thread_fn(void *arg1, void *arg2, void *arg3)
{
    (void)arg1; (void)arg2; (void)arg3;

    oled_display_init();

    while (1) {
        k_sem_take(&snapshot_sem, K_MSEC(500));

        k_mutex_lock(&snapshot_mutex, K_FOREVER);
        sensor_snapshot_t snap = latest_snapshot;
        k_mutex_unlock(&snapshot_mutex);

        k_mutex_lock(&mode_mutex, K_FOREVER);
        mode_t mode = current_mode;
        k_mutex_unlock(&mode_mutex);

        /* Only update display in non-monitor modes */
        if (mode != MODE_MONITOR) {
            oled_display_update(snap.field, snap.magnitude, snap.heading,
                                snap.dominant_pole, mode, snap.battery_pct);
        } else {
            oled_display_off(); /* Save power in monitor mode */
        }

        k_msleep(50); /* ~20Hz display refresh */
    }
}

/*---------------------------------------------------------------------------*/
/* Main entry point                                                           */
/*---------------------------------------------------------------------------*/
int main(void)
{
    LOG_INF("Flux Ring starting...");

    /* Initialize I2C */
    i2c_dev = DEVICE_DT_GET(I2C_NODE);
    if (!device_is_ready(i2c_dev)) {
        LOG_ERR("I2C device not ready");
        return -1;
    }

    /* Initialize power management */
    power_manager_init();

    /* Initialize sensors */
    mag_sensor_init(i2c_dev);
    accel_sensor_init(i2c_dev);
    baro_sensor_init(i2c_dev);

    /* Initialize peripherals */
    haptic_feedback_init(i2c_dev);
    led_feedback_init();
    touch_input_init(touch_mode_cb, touch_double_tap_cb);
    data_logger_init();

    /* Initialize semaphores */
    k_sem_init(&snapshot_sem, 0, 2);

    /* Launch threads */
    k_thread_create(&sensor_thread_data, sensor_stack,
                    K_THREAD_STACK_SIZEOF(sensor_stack),
                    sensor_thread_fn, NULL, NULL, NULL,
                    5, 0, K_NO_WAIT);

    k_thread_create(&ble_thread_data, ble_stack,
                    K_THREAD_STACK_SIZEOF(ble_stack),
                    ble_thread_fn, NULL, NULL, NULL,
                    4, 0, K_NO_WAIT);

    k_thread_create(&display_thread_data, display_stack,
                    K_THREAD_STACK_SIZEOF(display_stack),
                    display_thread_fn, NULL, NULL, NULL,
                    3, 0, K_NO_WAIT);

    LOG_INF("Flux Ring running — mode: EXPLORE");

    /* Main thread enters idle */
    while (1) {
        power_manager_idle();
        k_msleep(1000);
    }

    return 0;
}