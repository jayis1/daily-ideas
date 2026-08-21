/**
 * bme280.h — BME280 ambient temperature/humidity/pressure sensor (I2C)
 */
#ifndef BME280_H
#define BME280_H

#include "stm32g4xx_hal.h"

void bme280_init(void);
void bme280_read(float *temp, float *humidity, float *pressure);

#endif /* BME280_H */