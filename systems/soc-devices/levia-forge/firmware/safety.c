/*
 * Levia Forge — Safety Monitor
 * Checks lid interlock, tilt, battery, temperature, and emergency release.
 *
 * SPDX-License-Identifier: MIT
 */
#include "safety.h"
#include "sdkconfig.h"
#include "pico/stdlib.h"
#include "hardware/adc.h"
#include <math.h>

/* State struct (same layout as in main.c) */
typedef struct {
    float target_x, target_y, target_z;
    float actual_x, actual_y, actual_z;
    int pattern;
    int vortex_charge;
    float twin_delta;
    float bend_gradient;
    float transport_progress;
    float transport_speed;
    bool active;
    bool particle_detected;
    float particle_height_mm;
    int battery_mv;
    float temp_c;
    int safety;
    uint32_t uptime_ms;
    bool auto_track_z;
} safety_state_struct_t;

void safety_init(void)
{
    /* Configure safety input pins */
    gpio_init(PIN_SAFETY_REED);
    gpio_set_dir(PIN_SAFETY_REED, GPIO_IN);
    gpio_pull_up(PIN_SAFETY_REED);

    gpio_init(PIN_BTN_RELEASE);
    gpio_set_dir(PIN_BTN_RELEASE, GPIO_IN);
    gpio_pull_up(PIN_BTN_RELEASE);

    /* LSM6DSO tilt interrupt pin */
    gpio_init(PIN_TILT_IRQ);
    gpio_set_dir(PIN_TILT_IRQ, GPIO_IN);
    gpio_pull_up(PIN_TILT_IRQ);
}

int safety_check(void *state_ptr)
{
    safety_state_struct_t *s = (safety_state_struct_t *)state_ptr;

    /* 1. Check lid interlock (reed switch: LOW = open) */
    if (gpio_get(PIN_SAFETY_REED) == 0) {
        return SAFETY_LID_OPEN;
    }

    /* 2. Check tilt (LSM6DSO IRQ: LOW = tilt exceeded) */
    if (gpio_get(PIN_TILT_IRQ) == 0) {
        return SAFETY_TILT_EXCEEDED;
    }

    /* 3. Check battery voltage */
    if (s->battery_mv < BATTERY_LOW_MV) {
        if (s->battery_mv < BATTERY_CRIT_MV)
            return SAFETY_BATTERY_LOW;
        /* Low but not critical: warn but continue */
    }

    /* 4. Check temperature */
    if (s->temp_c > TEMP_MAX_C) {
        return SAFETY_OVERTEMP;
    }

    /* 5. Check emergency release button */
    if (gpio_get(PIN_BTN_RELEASE) == 0) {
        return SAFETY_EMERGENCY_RELEASE;
    }

    return SAFETY_OK;
}