/*
 * Therma Weave — Zone Controller
 * zone_controller.h — PID-controlled heating zone management
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef ZONE_CONTROLLER_H
#define ZONE_CONTROLLER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_timer.h"

#define NUM_ZONES       4
#define MIN_TARGET_TEMP  30.0f   /* °C minimum */
#define MAX_TARGET_TEMP  55.0f   /* °C maximum */
#define HARD_CUTOFF_TEMP 65.0f   /* °C hardware cutoff */
#define MAX_DUTY_PCT     95.0f   /* % maximum duty cycle */
#define PID_INTERVAL_US   250000  /* 250ms = 4 Hz */

/* PID state for one zone */
typedef struct {
    /* Zone identity */
    uint8_t zone_id;

    /* Target temperature (user-set, °C) */
    float target_temp;

    /* Activity offset (applied by IMU task) */
    float activity_offset;

    /* Effective target = target_temp + activity_offset */
    float effective_target;

    /* Current measured temperature (°C, from thermistor) */
    float current_temp;

    /* PID state */
    float kp;
    float ki;
    float kd;
    float integral;
    float prev_error;
    uint64_t last_pid_time;

    /* Output */
    float duty_pct;       /* 0–95% duty cycle */
    bool  enabled;

    /* Current draw (mA, from INA199) */
    float current_ma;

    /* Fault flags */
    bool fault_overtemp;
    bool fault_overcurrent;
    bool fault_thermistor_open;
    bool fault_thermistor_short;

    /* Auto-tune state */
    bool autotune_active;
    float autotune_peak_temp;
    float autotune_valley_temp;
    float autotune_ku;     /* Ultimate gain */
    float autotune_tu;     /* Ultimate period */
    int   autotune_cycles;

} zone_controller_t;

/**
 * Initialize a zone controller with default PID parameters.
 */
void zone_controller_init(zone_controller_t *zc, uint8_t zone_id);

/**
 * Update the current temperature reading for this zone.
 * Called by the temperature sensor task.
 */
void zone_controller_update_temp(zone_controller_t *zc, float temp_c);

/**
 * Compute PID output (duty cycle %) based on current error.
 * Called by the PID control task at 4 Hz.
 */
float zone_controller_pid_compute(zone_controller_t *zc, uint64_t now_us);

/**
 * Start Ziegler-Nichols auto-tune for this zone.
 * The zone will oscillate to find Ku and Tu, then set PID parameters.
 */
void zone_controller_autotune_start(zone_controller_t *zc);

/**
 * Reset all fault flags and re-enable the zone.
 */
void zone_controller_reset_faults(zone_controller_t *zc);

/**
 * Set target temperature with clamping to safe range.
 */
void zone_controller_set_target(zone_controller_t *zc, float target);

#endif /* ZONE_CONTROLLER_H */