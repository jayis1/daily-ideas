/*
 * Therma Weave — Zone Controller
 * zone_controller.c — PID-controlled heating zone management
 *
 * SPDX-License-Identifier: MIT
 */

#include "zone_controller.h"
#include <math.h>
#include "esp_log.h"

static const char *TAG = "ZONE_CTRL";

/* Default PID parameters (tuned for typical heated garment) */
#define DEFAULT_KP  2.5f
#define DEFAULT_KI  0.08f
#define DEFAULT_KD  0.4f

/* Anti-windup integral limit */
#define INTEGRAL_LIMIT  50.0f

void zone_controller_init(zone_controller_t *zc, uint8_t zone_id)
{
    zc->zone_id = zone_id;
    zc->target_temp = 40.0f;
    zc->activity_offset = 0.0f;
    zc->effective_target = 40.0f;
    zc->current_temp = 25.0f;  /* Assume room temperature at startup */

    zc->kp = DEFAULT_KP;
    zc->ki = DEFAULT_KI;
    zc->kd = DEFAULT_KD;
    zc->integral = 0.0f;
    zc->prev_error = 0.0f;
    zc->last_pid_time = 0;

    zc->duty_pct = 0.0f;
    zc->enabled = false;
    zc->current_ma = 0.0f;

    zc->fault_overtemp = false;
    zc->fault_overcurrent = false;
    zc->fault_thermistor_open = false;
    zc->fault_thermistor_short = false;

    zc->autotune_active = false;
    zc->autotune_peak_temp = 0.0f;
    zc->autotune_valley_temp = 0.0f;
    zc->autotune_ku = 0.0f;
    zc->autotune_tu = 0.0f;
    zc->autotune_cycles = 0;

    ESP_LOGI(TAG, "Zone %d initialized: target=%.1f°C, PID=(%.2f, %.4f, %.2f)",
             zone_id, zc->target_temp, zc->kp, zc->ki, zc->kd);
}

void zone_controller_update_temp(zone_controller_t *zc, float temp_c)
{
    /* Sanity check: thermistor open or short */
    if (temp_c < -40.0f || temp_c > 150.0f) {
        zc->fault_thermistor_open = (temp_c < -40.0f);
        zc->fault_thermistor_short = (temp_c > 150.0f);
        ESP_LOGE(TAG, "Zone %d: thermistor fault! temp=%.1f°C", zc->zone_id, temp_c);
        zc->enabled = false;
        return;
    }

    zc->current_temp = temp_c;

    /* Check hard over-temperature cutoff */
    if (temp_c >= HARD_CUTOFF_TEMP) {
        zc->fault_overtemp = true;
        zc->enabled = false;
        zc->duty_pct = 0.0f;
        ESP_LOGE(TAG, "Zone %d: OVERTEMP at %.1f°C! Disabled.", zc->zone_id, temp_c);
    }
}

float zone_controller_pid_compute(zone_controller_t *zc, uint64_t now_us)
{
    /* If zone is disabled or faulted, output 0% */
    if (!zc->enabled) {
        zc->integral = 0.0f;
        zc->duty_pct = 0.0f;
        return 0.0f;
    }

    /* Calculate effective target with activity offset */
    zc->effective_target = zc->target_temp + zc->activity_offset;

    /* Clamp effective target to safe range */
    if (zc->effective_target < MIN_TARGET_TEMP) zc->effective_target = MIN_TARGET_TEMP;
    if (zc->effective_target > MAX_TARGET_TEMP) zc->effective_target = MAX_TARGET_TEMP;

    /* Calculate error */
    float error = zc->effective_target - zc->current_temp;

    /* Calculate time delta in seconds */
    float dt;
    if (zc->last_pid_time == 0) {
        dt = 0.25f;  /* Assume 250ms for first iteration */
    } else {
        dt = (float)(now_us - zc->last_pid_time) / 1000000.0f;
        if (dt <= 0.0f || dt > 2.0f) dt = 0.25f;  /* Sanity clamp */
    }
    zc->last_pid_time = now_us;

    /* Proportional term */
    float p_term = zc->kp * error;

    /* Integral term with anti-windup */
    zc->integral += error * dt;
    if (zc->integral > INTEGRAL_LIMIT) zc->integral = INTEGRAL_LIMIT;
    if (zc->integral < -INTEGRAL_LIMIT) zc->integral = -INTEGRAL_LIMIT;
    float i_term = zc->ki * zc->integral;

    /* Derivative term (on error) */
    float derivative = (error - zc->prev_error) / dt;
    float d_term = zc->kd * derivative;
    zc->prev_error = error;

    /* Total PID output */
    float output = p_term + i_term + d_term;

    /* Clamp output to [0, MAX_DUTY_PCT] */
    if (output < 0.0f) output = 0.0f;
    if (output > MAX_DUTY_PCT) output = MAX_DUTY_PCT;

    zc->duty_pct = output;

    return output;
}

void zone_controller_set_target(zone_controller_t *zc, float target)
{
    if (target < MIN_TARGET_TEMP) target = MIN_TARGET_TEMP;
    if (target > MAX_TARGET_TEMP) target = MAX_TARGET_TEMP;

    zc->target_temp = target;
    ESP_LOGI(TAG, "Zone %d: target set to %.1f°C", zc->zone_id, target);
}

void zone_controller_reset_faults(zone_controller_t *zc)
{
    zc->fault_overtemp = false;
    zc->fault_overcurrent = false;
    zc->fault_thermistor_open = false;
    zc->fault_thermistor_short = false;
    zc->integral = 0.0f;
    zc->prev_error = 0.0f;
    zc->duty_pct = 0.0f;
    ESP_LOGI(TAG, "Zone %d: faults cleared", zc->zone_id);
}

void zone_controller_autotune_start(zone_controller_t *zc)
{
    zc->autotune_active = true;
    zc->autotune_cycles = 0;
    zc->autotune_peak_temp = 0.0f;
    zc->autotune_valley_temp = 1000.0f;
    zc->integral = 0.0f;
    zc->prev_error = 0.0f;
    ESP_LOGI(TAG, "Zone %d: auto-tune started", zc->zone_id);

    /* Auto-tune uses relay method:
     * - Apply 50% duty until temp rises past target
     * - Apply 0% duty until temp falls below target
     * - Measure oscillation amplitude and period
     * - Calculate Ku and Tu for Ziegler-Nichols
     * Then set: Kp = 0.6*Ku, Ki = 2*Kp/Tu, Kd = Kp*Tu/8
     */
}