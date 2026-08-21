/*
 * imu.h — ICM-42688-P self-motion compensation
 */

#ifndef IMU_H
#define IMU_H

#include <stdint.h>

typedef struct {
    float ax, ay, az;   /* acceleration, m/s² */
    float gx, gy, gz;   /* angular rate, rad/s */
    uint32_t t_ms;
} imu_sample_t;

void imu_init(void);
void imu_read(imu_sample_t *s);
/* Estimate device sway velocity (mm/s) along beam axis at time t */
float imu_compensate_velocity(const imu_sample_t *s, float t_ms);

#endif /* IMU_H */