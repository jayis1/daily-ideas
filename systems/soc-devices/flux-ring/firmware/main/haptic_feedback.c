/*
 * Flux Ring — haptic_feedback.c
 * DRV2603L haptic motor driver + vibration pattern engine.
 *
 * The DRV2603L is an I2C-controllable haptic driver with built-in
 * waveform library. For the Flux Ring, we use it to generate
 * field-strength-proportional vibration patterns.
 *
 * SPDX-License-Identifier: MIT
 */

#include "haptic_feedback.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/logging/log.h>

LOG_MODULE_DECLARE(haptic_feedback, LOG_LEVEL_INF);

static const struct device *i2c_dev;
static bool initialized = false;

/* GPIO for motor MOSFET (direct drive fallback) */
#define MOTOR_GPIO_NODE DT_NODELABEL(motor_en)
static const struct device *motor_gpio_dev;
#define MOTOR_PIN 24

/* Haptic state */
static float current_intensity = 0.0f;
static pole_t current_pole = POLE_NONE;
static int64_t last_pulse_time = 0;

/* DRV2603L registers */
#define DRV2603L_REG_STATUS     0x00
#define DRV2603L_REG_MODE      0x01
#define DRV2603L_REG_WAVESEQ1  0x02
#define DRV2603L_REG_WAVESEQ2  0x03
#define DRV2603L_REG_GO       0x0C
#define DRV2603L_REG_RATEDV    0x16
#define DRV2603L_REG_CLAMPV   0x17
#define DRV2603L_REG_AUTOCAL  0x1A
#define DRV2603L_REG_LIBRARY  0x0D

/* Mode bits */
#define DRV2603L_MODE_INTANE   0x00
#define DRV2603L_MODE_RAM      0x02
#define DRV2603L_MODE_DIAG     0x06

int haptic_feedback_init(const struct device *dev)
{
    i2c_dev = dev;

    /* Try to init DRV2603L over I2C */
    int rc = i2c_reg_write_byte(i2c_dev, DRV2603L_I2C_ADDR,
                                DRV2603L_REG_MODE, DRV2603L_MODE_INTANE);
    if (rc == 0) {
        /* Select haptic library 5 (typical ERM) */
        i2c_reg_write_byte(i2c_dev, DRV2603L_I2C_ADDR,
                           DRV2603L_REG_LIBRARY, 0x05);

        LOG_INF("DRV2603L haptic driver initialized");
        initialized = true;
    } else {
        LOG_WRN("DRV2603L not found, using GPIO direct drive fallback");
    }

    /* Configure motor GPIO as fallback */
    motor_gpio_dev = DEVICE_DT_GET(DT_NODELABEL(gpio0));
    if (device_is_ready(motor_gpio_dev)) {
        gpio_pin_configure(motor_gpio_dev, MOTOR_PIN, GPIO_OUTPUT_INACTIVE);
    }

    return 0;
}

void haptic_feedback_set_intensity(float magnitude_gauss, pole_t pole)
{
    current_intensity = magnitude_gauss;
    current_pole = pole;

    /* Determine pulse interval based on field strength */
    int interval_ms;
    if (magnitude_gauss < 0.5f) {
        /* Earth field — no vibration */
        haptic_feedback_off();
        return;
    } else if (magnitude_gauss < 1.0f) {
        interval_ms = 2000;
    } else if (magnitude_gauss < 3.0f) {
        interval_ms = 1000;
    } else if (magnitude_gauss < 10.0f) {
        interval_ms = 500;
    } else if (magnitude_gauss < 50.0f) {
        interval_ms = 250;
    } else {
        /* Very strong field — continuous */
        interval_ms = 0;
    }

    int64_t now = k_uptime_get();
    if (now - last_pulse_time >= interval_ms) {
        last_pulse_time = now;

        if (initialized) {
            /* Use DRV2603L waveform:
             * N-pole: waveform 14 (strong click)
             * S-pole: waveform 26 (double click)
             * None:   waveform 1 (minimum)
             */
            uint8_t waveform;
            if (pole == POLE_N) waveform = 14;
            else if (pole == POLE_S) waveform = 26;
            else waveform = 1;

            i2c_reg_write_byte(i2c_dev, DRV2603L_I2C_ADDR,
                               DRV2603L_REG_WAVESEQ1, waveform);
            i2c_reg_write_byte(i2c_dev, DRV2603L_I2C_ADDR,
                               DRV2603L_REG_WAVESEQ2, 0);
            i2c_reg_write_byte(i2c_dev, DRV2603L_I2C_ADDR,
                               DRV2603L_REG_GO, 0x01);
        } else {
            /* GPIO fallback: brief pulse */
            haptic_pulse(30 + (int)(magnitude_gauss * 0.5f));
        }
    }
}

void haptic_feedback_off(void)
{
    if (initialized) {
        i2c_reg_write_byte(i2c_dev, DRV2603L_I2C_ADDR,
                           DRV2603L_REG_GO, 0x00);
    }
    if (motor_gpio_dev && device_is_ready(motor_gpio_dev)) {
        gpio_pin_set(motor_gpio_dev, MOTOR_PIN, 0);
    }
}

void haptic_pulse(uint32_t duration_ms)
{
    if (motor_gpio_dev && device_is_ready(motor_gpio_dev)) {
        gpio_pin_set(motor_gpio_dev, MOTOR_PIN, 1);
        k_msleep(duration_ms);
        gpio_pin_set(motor_gpio_dev, MOTOR_PIN, 0);
    }
}