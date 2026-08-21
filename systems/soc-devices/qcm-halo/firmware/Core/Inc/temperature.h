/*
 * temperature.h — Peltier PID temperature control via ADS122U04 + PT1000
 */

#ifndef TEMPERATURE_H
#define TEMPERATURE_H

#include "config.h"

/* Initialize ADS122U04 and TEC PWM */
int temperature_init(void);

/* Read PT1000 temperature via ADS122U04 (4-wire ratiometric) */
float temperature_read(void);

/* PID control loop — call at 10 Hz.
 * Sets TEC PWM duty cycle and direction (heat/cool).
 * Returns current measured temperature.
 */
float temperature_pid_step(float target);

/* Enable/disable TEC */
void temperature_enable(void);
void temperature_disable(void);

/* Set target temperature with safety limits */
int  temperature_set_target(float target_c);

/* Get TEC current (A) from current-sense ADC */
float temperature_get_tec_current(void);

#endif /* TEMPERATURE_H */