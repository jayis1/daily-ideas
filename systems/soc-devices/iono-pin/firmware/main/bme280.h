/*
 * bme280.h — Bosch BME280 T/P/H over I2C1 for K0 normalization
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef BME280_H
#define BME280_H

#include <stdbool.h>

void bme280_init(void);
bool bme280_read(float *temp_c, float *pressure_kpa, float *hum_pct);

#endif /* BME280_H */