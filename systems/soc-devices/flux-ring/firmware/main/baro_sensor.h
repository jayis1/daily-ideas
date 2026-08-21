/*
 * Flux Ring — baro_sensor.h
 * MS5837-02BA barometric pressure sensor driver.
 * I2C address: 0x76
 */

#ifndef BARO_SENSOR_H_
#define BARO_SENSOR_H_

#include <zephyr/drivers/i2c.h>
#include <stdint.h>

#define MS5837_I2C_ADDR   0x76

/* Commands */
#define MS5837_RESET           0x1E
#define MS5837_ADC_READ       0x00
#define MS5837_CONVERT_D1_256 0x40
#define MS5837_CONVERT_D1_512 0x42
#define MS5837_CONVERT_D2_256 0x50
#define MS5837_CONVERT_D2_512 0x52
#define MS5837_PROM_READ      0xA0  /* 0xA0-0xAE, 7 coefficients */

typedef struct {
    float pressure_mbar;   /* Pressure in mbar (millibars) */
    float temperature_c;   /* Temperature in °C */
    float altitude_m;      /* Estimated altitude in meters */
} baro_data_t;

/**
 * Initialize MS5837-02BA over I2C.
 * Reads calibration PROM coefficients.
 */
int baro_sensor_init(const struct device *i2c_dev);

/**
 * Read pressure and temperature with oversampling.
 * Computes altitude from sea-level pressure (1013.25 mbar).
 */
int baro_sensor_read(baro_data_t *data);

#endif /* BARO_SENSOR_H_ */