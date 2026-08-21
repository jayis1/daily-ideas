/* imu.h — ICM-42688-P 6-axis IMU driver + Mahony attitude filter */
#ifndef IMU_H
#define IMU_H
#include "sky_lens.h"

void imu_init(void);
void imu_read_quat(float *w, float *x, float *y, float *z);  /* attitude quaternion */
void imu_read_accel(float *ax, float *ay, float *az);       /* m/s² */
void imu_read_gyro(float *gx, float *gy, float *gz);         /* rad/s */

#endif