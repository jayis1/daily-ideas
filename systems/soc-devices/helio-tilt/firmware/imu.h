/*
 * imu.h — LSM6DSO IMU + MMC5603NJ magnetometer fusion
 */

#ifndef IMU_H
#define IMU_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float roll;       /* degrees, rotation around X (pitch axis) */
    float pitch;      /* degrees, rotation around Y (roll axis) */
    float heading;    /* degrees, 0=N, 90=E, compass heading */
    float tilt_mag;   /* Total tilt magnitude (degrees) */
    bool   valid;
} imu_tilt_t;

/* Initialize I2C1 (LSM6DSO) + I2C2 (MMC5603NJ) */
void imu_init(void);

/* Read accelerometer + gyro, compute roll/pitch from gravity vector */
void imu_read_tilt(imu_tilt_t *tilt);

/* Read magnetometer, compute tilt-compensated heading */
void imu_read_heading(float *heading_deg);

/* Full fusion: roll + pitch + tilt-compensated heading */
void imu_read_fusion(imu_tilt_t *tilt);

/* Calibrate magnetometer (rotate device 360° in horizontal plane) */
void imu_calibrate_mag(void);

#endif /* IMU_H */