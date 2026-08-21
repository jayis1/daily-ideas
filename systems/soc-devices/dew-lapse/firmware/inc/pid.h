/* pid.h — generic PID controller with anti-windup */
#ifndef PID_H
#define PID_H

typedef struct {
    float kp, ki, kd;
    float integ;
    float prev_err;
    float out_min, out_max;
} pid_t;

void pid_init(pid_t *p, float kp, float ki, float kd,
              float out_min, float out_max);
float pid_step(pid_t *p, float setpoint, float measurement, float dt);
void pid_reset(pid_t *p);

#endif