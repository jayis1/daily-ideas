/* sensors.h — auxiliary sensors */
#ifndef SENSORS_H
#define SENSORS_H

int   sht45_read(float *t, float *rh);
int   bme280_init(void);
int   bme280_read(float *t, float *p, float *rh);
int   ms5837_read(float *p_pa, float *t_c);
int   scd41_init(void);
int   scd41_read(uint16_t *co2);
float coarse_dew_point(float t_air, float rh);

#endif