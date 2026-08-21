/*
 * fan_control.c — Suction fan trap control
 *
 * Drives a 30 mm brushless blower fan via a DRV8601 motor driver with
 * PWM soft-start to avoid current spikes. The fan runs for a configurable
 * duration (2 s default, 3 s for large moths) after a target pest is detected.
 *
 * The fan MOSFET gate is driven by ESP32-S3 LEDC channel 1 at 20 kHz.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "fan_control.h"
#include "esp_log.h"
#include "driver/ledc.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/timers.h"

static const char *TAG = "fan_control";

static TimerHandle_t s_fan_timer = NULL;
static bool s_fan_running = false;
static bool s_fault_detected = false;

static void fan_timer_callback(TimerHandle_t timer)
{
    (void)timer;
    /* Turn off the fan after the capture duration */
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1, 0);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1);
    s_fan_running = false;
    ESP_LOGI(TAG, "Fan OFF (timer expired)");
}

void fan_control_init(void)
{
    ESP_LOGI(TAG, "Initializing fan control (DRV8601, PWM %d kHz, soft-start %d ms)",
             FAN_PWM_FREQ_HZ / 1000, FAN_SOFTSTART_MS);

    /* Configure LEDC channel 1 for the fan PWM */
    ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_num  = LEDC_TIMER_1,
        .duty_resolution = FAN_PWM_RESOLUTION,
        .freq_hz    = FAN_PWM_FREQ_HZ,
        .clk_cfg    = LEDC_AUTO_CLK,
    };
    ledc_timer_config(&timer_cfg);

    ledc_channel_config_t chan_cfg = {
        .channel    = LEDC_CHANNEL_1,
        .duty       = 0,
        .gpio_num   = PIN_FAN_PWM,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .timer_sel  = LEDC_TIMER_1,
        .hpoint     = 0,
    };
    ledc_channel_config(&chan_cfg);

    /* Configure tachometer pin (input, optional) */
    gpio_set_direction(PIN_FAN_TACH, GPIO_MODE_INPUT);
    gpio_set_pull_mode(PIN_FAN_TACH, GPIO_PULLUP_ONLY);

    /* Create the one-shot fan timer */
    s_fan_timer = xTimerCreate("fan_timer",
                                pdMS_TO_TICKS(FAN_DURATION_MS),
                                pdFALSE, NULL, fan_timer_callback);

    s_fan_running = false;
    s_fault_detected = false;
}

void fan_control_capture(uint16_t duration_ms)
{
    if (s_fan_timer == NULL) return;

    /* Soft-start: ramp PWM from 0 to 100% over FAN_SOFTSTART_MS */
    int steps = 20;
    int step_delay = FAN_SOFTSTART_MS / steps;
    int max_duty = (1 << FAN_PWM_RESOLUTION) - 1;

    for (int i = 1; i <= steps; i++) {
        int duty = (max_duty * i) / steps;
        ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1, duty);
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1);
        vTaskDelay(pdMS_TO_TICKS(step_delay));
    }

    s_fan_running = true;

    /* Reset and start the one-shot timer */
    xTimerChangePeriod(s_fan_timer, pdMS_TO_TICKS(duration_ms), 0);
    xTimerStart(s_fan_timer, 0);
}

void fan_control_off(void)
{
    ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1, 0);
    ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_1);
    if (s_fan_timer) xTimerStop(s_fan_timer, 0);
    s_fan_running = false;
}

bool fan_control_check_fault(void)
{
    /* Read tachometer: if fan is running but tach is stuck high/low, it's faulty.
     * This is a simple heuristic — a full implementation would count tach
     * pulses over a window and compare to expected RPM. */
    if (s_fan_running) {
        int tach_val = gpio_get_level(PIN_FAN_TACH);
        (void)tach_val;  /* would need edge counting for real impl */
        /* For now, no fault — placeholder */
        s_fault_detected = false;
    }
    return s_fault_detected;
}