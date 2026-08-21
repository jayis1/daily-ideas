/**
 * spiro_flow/bme280.h — BME280 ambient sensor
 */
#ifndef SPIRO_FLOW_BME280_H
#define SPIRO_FLOW_BME280_H

#include "main.h"

int bme280_init(void);
int bme280_read(float *temp_c, float *pressure_mmhg, float *humidity_pct);

#endif