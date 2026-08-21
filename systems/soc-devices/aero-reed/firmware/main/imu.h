/*
 * imu.h — ICM-42688-P 6-axis IMU (SPI)
 */
#pragma once
#include <stdint.h>

void   imu_init(void);
void   imu_scan(void);
uint8_t imu_get_modulation(void);   /* 0..127 → CC1 */
float  imu_get_pitch_deg(void);     /* tilt angle */
float  imu_get_vibrato_rate(void);  /* Hz */
float  imu_get_vibrato_depth(void); /* cents */
int8_t imu_get_tilt_octave(void);   /* -1, 0, +1 */