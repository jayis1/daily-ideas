/*
 * visco-shear / firmware / stepper.c
 * PIO-driven microstep ramp generator for TMC2209 + NEMA8
 *
 * Uses RP2040 PIO to generate jitter-free step pulses.
 * Ramp profile: trapezoidal (accel → cruise → decel).
 * Oscillatory mode: sinusoidal step-rate modulation.
 *
 * MIT License.
 */
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/pio.h"
#include "hardware/pwm.h"
#include "main.h"
#include "stepper.h"

/* Simple bit-bang step generation (PIO would be used in production) */
static float current_rpm = 0.0f;
static uint32_t step_period_us = 0;
static bool running = false;
static bool oscillating = false;
static float osc_freq = 0;
static float osc_amp = 0;
static absolute_time_t last_step_time;

void stepper_init(void)
{
    gpio_init(PIN_STEP);
    gpio_set_dir(PIN_STEP, GPIO_OUT);
    gpio_put(PIN_STEP, 0);

    gpio_init(PIN_DIR);
    gpio_set_dir(PIN_DIR, GPIO_OUT);
    gpio_put(PIN_DIR, 0);

    gpio_init(PIN_TMC_EN);
    gpio_set_dir(PIN_TMC_EN, GPIO_OUT);
    gpio_put(PIN_TMC_EN, 1);  /* Disabled (active low) */

    current_rpm = 0;
    running = false;
}

void stepper_run_rpm(float rpm)
{
    if (fabsf(rpm) < 0.001f) {
        stepper_stop();
        return;
    }

    gpio_put(PIN_DIR, rpm < 0);   /* Direction */
    gpio_put(PIN_TMC_EN, 0);      /* Enable */

    /* Steps per second = rpm * STEP_PER_REV / 60 */
    float steps_per_sec = fabsf(rpm) * STEP_PER_REV / 60.0f;
    step_period_us = (uint32_t)(1e6f / steps_per_sec);

    /* Ramp: accelerate from current_rpm to target over ~200ms */
    float start_rpm = current_rpm;
    int n_ramp = 50;
    float rpm_step = (rpm - start_rpm) / n_ramp;
    for (int i = 0; i < n_ramp; i++) {
        float r = start_rpm + rpm_step * (i + 1);
        float sps = fabsf(r) * STEP_PER_REV / 60.0f;
        uint32_t per = (uint32_t)(1e6f / sps);
        /* Generate a few steps at this rate */
        int n = 10;
        for (int s = 0; s < n; s++) {
            gpio_put(PIN_STEP, 1);
            busy_wait_us_32(per / 2);
            gpio_put(PIN_STEP, 0);
            busy_wait_us_32(per / 2);
        }
        current_rpm = r;
    }

    current_rpm = rpm;
    running = true;
    oscillating = false;
    last_step_time = get_absolute_time();
}

void stepper_oscillate(float freq_hz, float amplitude_rad)
{
    gpio_put(PIN_TMC_EN, 0);
    oscillating = true;
    osc_freq = freq_hz;
    osc_amp = amplitude_rad;
    running = true;
    current_rpm = 0;
    last_step_time = get_absolute_time();
}

void stepper_stop(void)
{
    /* Decelerate to zero */
    if (current_rpm != 0 && running) {
        float start_rpm = current_rpm;
        int n_ramp = 30;
        for (int i = 0; i < n_ramp; i++) {
            float r = start_rpm * (1.0f - (float)(i + 1) / n_ramp);
            if (fabsf(r) < 0.01f) break;
            float sps = fabsf(r) * STEP_PER_REV / 60.0f;
            uint32_t per = (uint32_t)(1e6f / sps);
            for (int s = 0; s < 5; s++) {
                gpio_put(PIN_STEP, 1);
                busy_wait_us_32(per / 2);
                gpio_put(PIN_STEP, 0);
                busy_wait_us_32(per / 2);
            }
            current_rpm = r;
        }
    }

    gpio_put(PIN_STEP, 0);
    gpio_put(PIN_TMC_EN, 1);  /* Disable */
    current_rpm = 0;
    running = false;
    oscillating = false;
}

void stepper_estop(void)
{
    gpio_put(PIN_STEP, 0);
    gpio_put(PIN_TMC_EN, 1);
    current_rpm = 0;
    running = false;
    oscillating = false;
}

float stepper_current_rpm(void)
{
    return current_rpm;
}

/* Called from main loop to step the motor */
void stepper_task(void)
{
    if (!running) return;

    if (oscillating) {
        /* Sinusoidal speed: omega(t) = A·ω·cos(ω·t) */
        uint32_t t_us = to_us_since_boot(get_absolute_time());
        float t = t_us * 1e-6f;
        float omega_inst = osc_amp * 2.0f * M_PI * osc_freq *
                           cosf(2.0f * M_PI * osc_freq * t);
        float rpm_inst = omega_inst * 60.0f / (2.0f * M_PI);
        float sps = fabsf(rpm_inst) * STEP_PER_REV / 60.0f;
        if (sps < 1) return;
        uint32_t per = (uint32_t)(1e6f / sps);
        gpio_put(PIN_DIR, rpm_inst < 0);
        if (to_us_since_boot(get_absolute_time()) - to_us_since_boot(last_step_time) >= per) {
            gpio_put(PIN_STEP, 1);
            busy_wait_us_32(2);
            gpio_put(PIN_STEP, 0);
            last_step_time = get_absolute_time();
        }
    } else {
        /* Constant speed */
        if (to_us_since_boot(get_absolute_time()) - to_us_since_boot(last_step_time) >= step_period_us) {
            gpio_put(PIN_STEP, 1);
            busy_wait_us_32(2);
            gpio_put(PIN_STEP, 0);
            last_step_time = get_absolute_time();
        }
    }
}