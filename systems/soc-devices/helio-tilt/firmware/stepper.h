/*
 * stepper.h — NEMA8 AZ/EL stepper motor control
 */

#ifndef STEPPER_H
#define STEPPER_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    AXIS_AZIMUTH,
    AXIS_ELEVATION,
} stepper_axis_t;

/* Initialize stepper GPIO + timers */
void stepper_init(void);

/* Move one axis to an absolute angle (degrees).
 * AZ: 0–360, EL: 0–90.
 * Blocks until move complete (simplified; real impl would use timer IRQ).
 */
void stepper_move_to(stepper_axis_t axis, float target_deg);

/* Get current angle of an axis */
float stepper_get_angle(stepper_axis_t axis);

/* Home an axis using limit switch (find 0° reference) */
int stepper_home(stepper_axis_t axis);

/* Stop immediately */
void stepper_stop(stepper_axis_t axis);

/* Enable/disable stepper (power save) */
void stepper_enable(stepper_axis_t axis, bool en);

#endif /* STEPPER_H */