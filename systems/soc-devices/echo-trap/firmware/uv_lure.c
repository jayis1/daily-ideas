/*
 * uv_lure.c — 395nm UV LED lure scheduling
 *
 * The UV LED array attracts nocturnal pests (moths, mosquitoes). It is
 * duty-cycled at night (30% brightness, 15 min on / 5 min off) and turned
 * off during the day to conserve battery. The TSL2591 ambient light sensor
 * determines day vs. night.
 *
 * Driven by ESP32-S3 LEDC channel 0 at 1 kHz, 8-bit resolution.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "uv_lure.h"
#include "esp_log.h"
#include "driver/ledc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "uv_lure";

static uint8_t s_override_duty = 0;   /* 0 = no override, >0 = fixed duty */
static bool s_is_night = false;
static uint32_t s_cycle_start_s = 0;  /* start of current on/off cycle */

void uv_lure_init(void)
{
    ESP_LOGI(TAG, "Initializing UV lure (395 nm, LEDC ch0, %d Hz)",
             UV_PWM_FREQ_HZ);

    ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_num  = LEDC_TIMER_0,
        .duty_resolution = UV_PWM_RESOLUTION,
        .freq_hz    = UV_PWM_FREQ_HZ,
        .clk_cfg    = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&timer_cfg);

    ledc_channel_config_t chan_cfg = {
        .channel    = LEDC_CHANNEL_0,
        .duty       = 0,
        .gpio_num   = PIN_UV_LED,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_sel  = LEDC_TIMER_0,
        .hpoint     = 0,
    };
    ledc_channel_config(&chan_cfg);
}

void uv_lure_update(float ambient_lux)
{
    /* Determine day vs. night */
    s_is_night = (ambient_lux < UV_NIGHT_LUX_THRESH);

    if (s_override_duty > 0) {
        /* Override mode: fixed duty */
        ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, s_override_duty);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
        return;
    }

    if (!s_is_night) {
        /* Daytime: UV off */
        ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, UV_DUTY_DAY_OFF);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
        return;
    }

    /* Night: duty cycle 15 min on, 5 min off (20 min cycle) */
    uint32_t now_s = (uint32_t)(esp_timer_get_time() / 1000000ULL);
    uint32_t cycle_pos = (now_s - s_cycle_start_s) % 1200;  /* 20 min cycle */
    if (cycle_pos < 900) {
        /* 15 min ON at 30% duty */
        ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, UV_DUTY_NIGHT_LOW);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
    } else {
        /* 5 min OFF */
        ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
    }
}

void uv_lure_off(void)
{
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
    s_override_duty = 0;
}

void uv_lure_override(uint8_t duty)
{
    s_override_duty = duty;
    if (duty > 0) {
        ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0);
        ESP_LOGI(TAG, "UV override: %d/255 duty", duty);
    }
}