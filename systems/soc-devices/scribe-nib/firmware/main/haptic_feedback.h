/*
 * haptic_feedback.h — Vibration motor driver API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef HAPTIC_FEEDBACK_H
#define HAPTIC_FEEDBACK_H

#include "esp_err.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include <stdint.h>

/* Haptic pattern element */
typedef struct {
    uint8_t duty;      /* 0-255 PWM duty cycle */
    uint16_t on_ms;    /* On duration in ms */
    uint16_t off_ms;   /* Off gap duration in ms */
} haptic_pattern_t;

/**
 * @brief Initialize haptic feedback motor driver.
 *
 * @param pin      GPIO pin connected to MOSFET gate
 * @param timer    LEDC timer to use
 * @param channel  LEDC channel to use
 */
esp_err_t haptic_feedback_init(gpio_num_t pin, ledc_timer_t timer, ledc_channel_t channel);

/**
 * @brief Single vibration pulse.
 * @param duration_ms  Pulse duration in ms
 */
esp_err_t haptic_feedback_pulse(uint32_t duration_ms);

/**
 * @brief Double vibration pulse (for confirmations).
 * @param pulse_ms  Each pulse duration in ms
 */
esp_err_t haptic_feedback_double(uint32_t pulse_ms);

/**
 * @brief Custom haptic pattern.
 * @param pattern  Array of on/off/duty elements
 * @param count    Number of elements
 */
esp_err_t haptic_feedback_pattern(const haptic_pattern_t *pattern, int count);

#endif /* HAPTIC_FEEDBACK_H */