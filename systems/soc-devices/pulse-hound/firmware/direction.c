/*
 * Pulse Hound — RF Signal Hunter
 * direction.c — 28BYJ-48 stepper driver, 360-degree RSSI pattern,
 *               parabolic peak interpolation, bearing computation
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "direction.h"
#include "rf_detector.h"
#include "config.h"
#include <math.h>
#include <string.h>

/* ---- I2C/GPIO HAL stubs ---- */
extern void gpio_set(int pin, int val);
extern void delay_ms(uint32_t ms);
extern uint32_t rtc_get_time_s(void);

/* ---- 28BYJ-48 half-step sequence (8 steps) ---- */
/* Each step energizes two coils; 8-step half sequence for smoother motion */
static const int half_step_seq[8][4] = {
    {1, 0, 0, 0},
    {1, 1, 0, 0},
    {0, 1, 0, 0},
    {0, 1, 1, 0},
    {0, 0, 1, 0},
    {0, 0, 1, 1},
    {0, 0, 0, 1},
    {1, 0, 0, 1},
};

static int current_step_idx = 0;
static int stepper_initialized = 0;
static int current_bearing_deg = 0; /* 0–359, relative to home sensor */

/* ---- Stepper control ---- */
static void stepper_step(int direction)
{
    current_step_idx = (current_step_idx + direction + 8) % 8;
    const int *seq = half_step_seq[current_step_idx];
    gpio_set(STEPPER_IN1_GPIO, seq[0]);
    gpio_set(STEPPER_IN2_GPIO, seq[1]);
    gpio_set(STEPPER_IN3_GPIO, seq[2]);
    gpio_set(STEPPER_IN4_GPIO, seq[3]);
    /* 28BYJ-48 at 5V: ~2 ms minimum between half-steps */
    delay_ms(3);
}

static void stepper_power_on(void)
{
    gpio_set(STEPPER_POWER_GPIO, 1);
    delay_ms(10);
}

static void stepper_power_off(void)
{
    /* De-energize all coils */
    gpio_set(STEPPER_IN1_GPIO, 0);
    gpio_set(STEPPER_IN2_GPIO, 0);
    gpio_set(STEPPER_IN3_GPIO, 0);
    gpio_set(STEPPER_IN4_GPIO, 0);
    delay_ms(5);
    gpio_set(STEPPER_POWER_GPIO, 0);
}

/* ---- Home the antenna to 0° using reed switch ---- */
int direction_home(void)
{
    stepper_power_on();
    delay_ms(50);

    /* Rotate up to 360° looking for the home sensor */
    for (int i = 0; i < STEPPER_STEPS_PER_REV; i++) {
        /* Read reed switch (active low = home) */
        extern int gpio_read(int pin);
        if (gpio_read(STEPPER_HOME_GPIO) == 0) {
            current_bearing_deg = 0;
            current_step_idx = 0;
            stepper_power_off();
            return 0;
        }
        stepper_step(1);
    }

    /* No home found — just set current position as 0° */
    current_bearing_deg = 0;
    stepper_power_off();
    return -1;
}

/* ---- Full 360° direction-finding sweep ---- */
int direction_find_bearing(float *bearing_deg, float *peak_rssi_dbm)
{
    float rssi_pattern[STEPPER_DF_STEPS];
    float samples[50];
    int step_indices[STEPPER_DF_STEPS];

    stepper_power_on();
    delay_ms(50);

    /* Home first */
    extern int gpio_read(int pin);
    int homed = 0;
    for (int i = 0; i < STEPPER_STEPS_PER_REV && !homed; i++) {
        if (gpio_read(STEPPER_HOME_GPIO) == 0)
            homed = 1;
        else
            stepper_step(1);
    }
    current_bearing_deg = 0;
    current_step_idx = 0;

    /* Rotate through 360° in DF_STEPS steps */
    int steps_per_df_step = STEPPER_STEPS_PER_REV / STEPPER_DF_STEPS; /* 2048/64 = 32 */

    for (int df_step = 0; df_step < STEPPER_DF_STEPS; df_step++) {
        /* Rotate to this azimuth */
        for (int s = 0; s < steps_per_df_step; s++)
            stepper_step(1);

        /* Settle */
        delay_ms(STEPPER_SETTLE_MS);

        /* Sample RSSI */
        int n_samples = STEPPER_SAMPLE_MS / 10; /* 50 samples @ ~10 ms each */
        if (n_samples > 50) n_samples = 50;
        int got = rf_detector_sample_burst(samples, n_samples, 10);
        if (got > 0)
            rssi_pattern[df_step] = rf_detector_median_rssi(samples, got);
        else
            rssi_pattern[df_step] = RSSI_NOISE_FLOOR_DBM;

        step_indices[df_step] = df_step;
    }

    /* De-energize stepper */
    stepper_power_off();

    /* Find peak */
    int peak_idx = 0;
    float peak_val = rssi_pattern[0];
    for (int i = 1; i < STEPPER_DF_STEPS; i++) {
        if (rssi_pattern[i] > peak_val) {
            peak_val = rssi_pattern[i];
            peak_idx = i;
        }
    }

    /* Parabolic interpolation for sub-step accuracy */
    float y0 = rssi_pattern[(peak_idx - 1 + STEPPER_DF_STEPS) % STEPPER_DF_STEPS];
    float y1 = rssi_pattern[peak_idx];
    float y2 = rssi_pattern[(peak_idx + 1) % STEPPER_DF_STEPS];

    /* Parabolic peak offset: -0.5 * (y2 - y0) / (y2 - 2*y1 + y0) */
    float denom = y2 - 2.0f * y1 + y0;
    float offset = 0.0f;
    if (fabsf(denom) > 0.01f)
        offset = -0.5f * (y2 - y0) / denom;
    /* Clamp offset to ±0.5 step */
    if (offset > 0.5f)  offset = 0.5f;
    if (offset < -0.5f) offset = -0.5f;

    /* Bearing in degrees: each step = 360/64 = 5.625° */
    float bearing = (peak_idx + offset) * (360.0f / STEPPER_DF_STEPS);
    if (bearing < 0) bearing += 360.0f;
    if (bearing >= 360.0f) bearing -= 360.0f;

    *bearing_deg = bearing;
    *peak_rssi_dbm = peak_val;
    current_bearing_deg = (int)bearing;

    return 0;
}

/* ---- Get last known bearing ---- */
int direction_get_bearing(void)
{
    return current_bearing_deg;
}

/* ---- Init ---- */
void direction_init(void)
{
    if (stepper_initialized) return;
    stepper_initialized = 1;
    gpio_set(STEPPER_POWER_GPIO, 0);
    gpio_set(STEPPER_IN1_GPIO, 0);
    gpio_set(STEPPER_IN2_GPIO, 0);
    gpio_set(STEPPER_IN3_GPIO, 0);
    gpio_set(STEPPER_IN4_GPIO, 0);
}