/* bme280.h — BME280 atmospheric sensor driver (I2C) */

#ifndef BME280_H
#define BME280_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float temperature;   /* °C */
    float pressure;      /* Pa */
    float humidity;      /* %RH */
    /* Derived quantities */
    float mixing_ratio;  /* kg/kg */
    float air_density;   /* kg/m³ */
} bme280_data_t;

bool bme280_init(void);

bool bme280_read(bme280_data_t *data);

/* Compute mixing ratio from T, P, RH */
float bme280_mixing_ratio(float temp_c, float rh_percent, float pressure_pa);

/* Compute air density */
float bme280_air_density(float temp_c, float rh_percent, float pressure_pa);

#endif /* BME280_H */