/*
 * port_sim.h — host simulation shim declarations for Sky Lens
 *
 * These functions are implemented in port_sim.c and are only available
 * when SKY_LENS_SIM=1 is defined. They stub the ESP32 HAL so the firmware
 * math path can be compiled and run on a host.
 */
#ifndef PORT_SIM_H
#define PORT_SIM_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/* Time */
void     port_sim_init(void);
void     port_sim_step(void);
bool     port_sim_done(void);
uint64_t port_sim_now_us(void);

/* Logging */
void port_sim_log(const char *fmt, ...);

/* Date string (YYYYMMDD) */
void port_sim_date(char *buf, int len);

/* ADC shim */
void port_sim_set_next_adc(int16_t h0, int16_t h1);
void port_sim_adc_read(int16_t *h0, int16_t *h1);

/* IMU shim */
void port_sim_imu_quat(float *w, float *x, float *y, float *z);
void port_sim_imu_accel(float *ax, float *ay, float *az);
void port_sim_imu_gyro(float *gx, float *gy, float *gz);

/* Pressure / temp shim */
float port_sim_pressure_hpa(void);
float port_sim_temp_c(void);

#endif /* PORT_SIM_H */