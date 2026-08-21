/*
 * ambient.h — ambient temperature/humidity/pressure
 *
 * SHT45 (I2C) for T/RH (fast, for humidity-correction of particle mass)
 * BME280 (I2C, secondary addr) for pressure + backup T/RH
 */

#ifndef AMBIENT_H
#define AMBIENT_H

#include <stdbool.h>

void   ambient_init(void);
bool   ambient_read(float *temp_c, float *rh_pct, float *pres_hpa);

#endif /* AMBIENT_H */