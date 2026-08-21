/*
 * visco-shear / firmware / spindle.h
 * Spindle geometry constants + ID detection
 */
#ifndef VISCO_SHEAR_SPINDLE_H
#define VISCO_SHEAR_SPINDLE_H

#include "main.h"

void spindle_init(void);

/* Detect spindle type from ID resistor (ADC) */
spindle_type_t spindle_detect(void);

/* Get spindle name */
const char *spindle_name(spindle_type_t sp);

/* Get geometry struct */
const spindle_geo_t *spindle_geo(spindle_type_t sp);

/* Compute shear rate for given angular velocity [rad/s] */
float spindle_shear_rate(spindle_type_t sp, float omega);

/* Compute torque-to-stress conversion factor [Pa/µN·m] */
float spindle_torque_to_stress_factor(spindle_type_t sp);

#endif