/*
 * visco-shear / firmware / stepper.h
 * PIO-driven microstep ramp generator for TMC2209 + NEMA8
 */
#ifndef VISCO_SHEAR_STEPPER_H
#define VISCO_SHEAR_STEPPER_H

#include <stdint.h>
#include <stdbool.h>

void stepper_init(void);

/* Run at constant RPM (ramped acceleration) */
void stepper_run_rpm(float rpm);

/* Oscillate sinusoidally: freq [Hz], amplitude [rad] */
void stepper_oscillate(float freq_hz, float amplitude_rad);

/* Stop motor (decelerate then disable) */
void stepper_stop(void);

/* Emergency stop (immediate) */
void stepper_estop(void);

/* Get current RPM */
float stepper_current_rpm(void);

#endif