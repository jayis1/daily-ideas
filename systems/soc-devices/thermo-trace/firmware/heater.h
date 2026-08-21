/*
 * heater.h — Dual PID heater control (header)
 */
#ifndef HEATER_H
#define HEATER_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float setpoint;      /* target temperature (°C) */
    float kP;            /* proportional gain */
    float kI;            /* integral gain */
    float kD;            /* derivative gain */
    float integral;      /* integral accumulator */
    float prev_error;    /* previous error for derivative */
    float output;        /* current PID output (0.0–1.0) */
    float max_output;    /* saturation limit */
    float max_integral;  /* anti-windup limit */
} pid_t;

void    heater_init(void);
void    heater_set_pwm(uint8_t channel, float duty);
void    heater_enable(bool on);
void    heater_off(void);
void    pid_init(pid_t *pid, float kp, float ki, float kd, float max_out, float max_int);
float   pid_update(pid_t *pid, float measured, float setpoint, float dt);
void    pid_reset(pid_t *pid);
float   heater_get_power(uint8_t channel);
float   heater_compute_power(float v_supply, float duty, float r_heater);

#endif /* HEATER_H */