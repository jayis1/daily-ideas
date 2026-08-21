/* bme280.h — BME280 temperature/humidity/pressure sensor driver (I2C) */

#ifndef TASTE_BEAD_BME280_H
#define TASTE_BEAD_BME280_H

#include "esp_err.h"
#include <stdint.h>

typedef struct {
    float temperature;  /* °C */
    float humidity;     /* %RH */
    float pressure;     /* hPa */
} bme280_data_t;

/* Initialize BME280 on I2C bus */
esp_err_t bme280_init(int sda_pin, int scl_pin);

/* Read compensated data */
esp_err_t bme280_read(bme280_data_t *data);

#endif /* TASTE_BEAD_BME280_H */