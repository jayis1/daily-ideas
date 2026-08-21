/*
 * dent-scope / Core/Inc/imu.h
 * Dent Scope — ICM-42688-P IMU driver for leveling
 * MIT License.
 */
#ifndef IMU_H
#define IMU_H

#include "main.h"

void  imu_init(void);
float imu_get_tilt_deg(void);
float imu_get_roll_deg(void);
bool  imu_is_level(void);

#endif /* IMU_H */