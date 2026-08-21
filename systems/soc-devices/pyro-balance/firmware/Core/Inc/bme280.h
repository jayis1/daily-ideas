/*
 * pyro-balance / Core/Inc/bme280.h
 */
#ifndef BME280_H
#define BME280_H
#include "main.h"
void  bme280_init(void);
float bme280_temp(void);
float bme280_humidity(void);
float bme280_pressure(void);
#endif