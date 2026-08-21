/*
 * visco-shear / firmware / torque.h
 * ADS1115 + DRV5053 Hall torque sensor acquisition
 */
#ifndef VISCO_SHEAR_TORQUE_H
#define VISCO_SHEAR_TORQUE_H

#include <stdint.h>
#include <stdbool.h>

void torque_init(void);

/* Read single torque sample (µN·m), differential Hall */
float torque_read_single(void);

/* Read averaged torque (n samples) */
float torque_read_averaged(int n);

/* Auto-zero: record zero-torque baseline */
void torque_auto_zero(void);

/* Set calibration factor */
void torque_set_calibration(float cf);

/* Get calibration factor */
float torque_get_calibration(void);

#endif