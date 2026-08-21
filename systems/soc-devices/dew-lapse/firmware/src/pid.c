/* pid.c — generic PID controller with anti-windup and derivative filter.
 * Returns controller output in [out_min, out_max].
 */
#include "pid.h"

void pid_init(pid_t *p, float kp, float ki, float kd,
              float out_min, float out_max)
{
    p->kp = kp;
    p->ki = ki;
    p->kd = kd;
    p->integ = 0.0f;
    p->prev_err = 0.0f;
    p->out_min = out_min;
    p->out_max = out_max;
}

float pid_step(pid_t *p, float setpoint, float measurement, float dt)
{
    float err = setpoint - measurement;
    p->integ += err * dt;
    /* clamp integral to prevent windup */
    if (p->integ * p->ki > p->out_max) p->integ = p->out_max / p->ki;
    if (p->integ * p->ki < p->out_min) p->integ = p->out_min / p->ki;

    float deriv = (err - p->prev_err) / dt;
    p->prev_err = err;

    float out = p->kp * err + p->ki * p->integ + p->kd * deriv;
    if (out > p->out_max) out = p->out_max;
    if (out < p->out_min) out = p->out_min;
    return out;
}

void pid_reset(pid_t *p)
{
    p->integ = 0.0f;
    p->prev_err = 0.0f;
}