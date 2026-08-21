/**
 * lumen_cast/firmware/motor.h — TMC2209 stepper motor driver
 */
#ifndef LUMEN_CAST_MOTOR_H
#define LUMEN_CAST_MOTOR_H

void motor_init(void);
void motor_enable(bool en);
void motor_set_dir(bool clockwise);
void motor_move_to_deg(float target_deg, float rpm);
void motor_step(int steps);
bool motor_at_target(void);
float motor_get_position_deg(void);
void motor_home(void);

#endif