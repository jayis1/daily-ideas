/*
 * haptic_feedback.c — Vibration motor driver for Scribe Nib
 *
 * Drives a 4mm coin vibration motor via PWM on MOSFET gate.
 * Provides single pulse, double pulse, and pattern feedback.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "haptic_feedback.h"
#include "esp_log.h"
#include "driver/ledc.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "haptic";

static gpio_num_t motor_pin = GPIO_NUM_42;
static ledc_timer_t ledc_timer = LEDC_TIMER_0;
static ledc_channel_t ledc_channel = LEDC_CHANNEL_0;
static bool initialized = false;

esp_err_t haptic_feedback_init(gpio_num_t pin, ledc_timer_t timer, ledc_channel_t channel)
{
    motor_pin = pin;
    ledc_timer = timer;
    ledc_channel = channel;

    /* Configure LEDC PWM for vibration motor */
    ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LEDC_TIMER_8_BIT,
        .timer_num = timer,
        .freq_hz = 200,  /* 200Hz PWM for smooth vibration */
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_ERROR_CHECK(ledc_timer_config(&timer_cfg));

    ledc_channel_config_t channel_cfg = {
        .gpio_num = pin,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = channel,
        .timer_sel = timer,
        .duty = 0,          /* Start with motor off */
        .hpoint = 0,
    };
    ESP_ERROR_CHECK(ledc_channel_config(&channel_cfg));

    initialized = true;
    ESP_LOGI(TAG, "Haptic feedback initialized on GPIO%d (PWM 200Hz)", pin);
    return ESP_OK;
}

esp_err_t haptic_feedback_pulse(uint32_t duration_ms)
{
    if (!initialized) return ESP_ERR_INVALID_STATE;

    /* Full power (duty = 255) */
    ledc_set_duty(LEDC_LOW_SPEED_MODE, ledc_channel, 200);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, ledc_channel);

    vTaskDelay(pdMS_TO_TICKS(duration_ms));

    /* Off */
    ledc_set_duty(LEDC_LOW_SPEED_MODE, ledc_channel, 0);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, ledc_channel);

    return ESP_OK;
}

esp_err_t haptic_feedback_double(uint32_t pulse_ms)
{
    if (!initialized) return ESP_ERR_INVALID_STATE;

    haptic_feedback_pulse(pulse_ms);
    vTaskDelay(pdMS_TO_TICKS(pulse_ms));  /* Gap = same as pulse */
    haptic_feedback_pulse(pulse_ms);

    return ESP_OK;
}

esp_err_t haptic_feedback_pattern(const haptic_pattern_t *pattern, int count)
{
    if (!initialized) return ESP_ERR_INVALID_STATE;

    for (int i = 0; i < count; i++) {
        if (pattern[i].on_ms > 0) {
            ledc_set_duty(LEDC_LOW_SPEED_MODE, ledc_channel, pattern[i].duty);
            ledc_update_duty(LEDC_LOW_SPEED_MODE, ledc_channel);
            vTaskDelay(pdMS_TO_TICKS(pattern[i].on_ms));
        }
        if (pattern[i].off_ms > 0) {
            ledc_set_duty(LEDC_LOW_SPEED_MODE, ledc_channel, 0);
            ledc_update_duty(LEDC_LOW_SPEED_MODE, ledc_channel);
            vTaskDelay(pdMS_TO_TICKS(pattern[i].off_ms));
        }
    }

    /* Ensure motor is off */
    ledc_set_duty(LEDC_LOW_SPEED_MODE, ledc_channel, 0);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, ledc_channel);

    return ESP_OK;
}