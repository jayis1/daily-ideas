/*
 * dent-scope / Core/Inc/stepper.h
 * Dent Scope — 28BYJ-48 stepper + DRV8833 driver
 * MIT License.
 */
#ifndef STEPPER_H
#define STEPPER_H

#include "main.h"

void stepper_init(void);
void stepper_approach(void);
void stepper_tick_approach(void);
void stepper_step_down(void);
void stepper_step_up(void);
void stepper_stop(void);
void stepper_hold_position(void);
void stepper_retract(void);
void stepper_tick_retract(void);
void stepper_emergency_stop(void);
bool stepper_is_retracted(void);

#endif /* STEPPER_H */