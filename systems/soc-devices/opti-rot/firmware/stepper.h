/*
 * stepper.h — 28BYJ-48 stepper motor driver
 * Drives the analyzer polarizer through 4096 half-steps per revolution (0.088°/step).
 */
#ifndef STEPPER_H
#define STEPPER_H

#include <stdint.h>
#include <stdbool.h>

/* 28BYJ-48 half-step sequence (8 states per cycle, 4096 steps/rev with gearbox) */
#define STEPPER_SEQ_LEN 8

/* Public API */
void stepper_init(void);
void stepper_move_to(double angle_deg);       /* absolute angle */
void stepper_step(int16_t steps);              /* relative steps */
void stepper_deenergize(void);                 /* power off coils */
double stepper_get_angle(void);                /* current angle in degrees */
bool stepper_is_moving(void);
void stepper_home(void);                       /* find mechanical home (optical limit) */

#endif /* STEPPER_H */