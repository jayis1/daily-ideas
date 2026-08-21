/*
 * gossamer-spin / firmware / collector.c
 * NEMA8 stepper + belt drive rotating drum collector.
 *
 * Drum RPM is controlled by the TIM8 step pulse frequency.
 * 1:1 belt ratio, 200 steps/rev, 16× microstepping.
 *
 * RPM = step_rate × 60 / (steps_per_rev × microsteps × belt_ratio)
 * step_rate = RPM × steps_per_rev × microsteps × belt_ratio / 60
 */
#include "main.h"

static struct {
    float target_rpm;
    bool  running;
} drum = { 0 };

static void *h_tim8 = (void *)1;

static float rpm_to_step_rate(float rpm)
{
    return rpm * DRUM_STEPS_PER_REV * DRUM_MICROSTEPS * DRUM_BELT_RATIO / 60.0f;
}

void collector_init(void)
{
    drum.target_rpm = 0.0f;
    drum.running = false;

    /* Configure TIM8 for step pulse generation:
       - Output compare, toggle mode on CH1 (step)
       - CH2 as GPIO direction output
       - Start disabled */
    (void)h_tim8;
}

void collector_set_rpm(float rpm)
{
    if (rpm < 0.0f) rpm = 0.0f;
    if (rpm > DRUM_MAX_RPM) rpm = DRUM_MAX_RPM;
    drum.target_rpm = rpm;

    if (drum.running) {
        float step_rate = rpm_to_step_rate(rpm);
        /* Update TIM8 ARR for new frequency */
        (void)step_rate;
    }
}

void collector_start(void)
{
    drum.running = true;
    float step_rate = rpm_to_step_rate(drum.target_rpm);
    /* Set DIR pin
       Set TIM8 ARR for step_rate
       Enable TIM8 */
    (void)step_rate;
}

void collector_stop(void)
{
    drum.running = false;
    /* Disable TIM8 */
}