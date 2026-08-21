/*
 * ds18b20.h — DS18B20 1-Wire drift-tube wall temperature
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef DS18B20_H
#define DS18B20_H

#include <stdbool.h>

void ds18b20_init(void);
bool ds18b20_read(float *temp_c);

#endif /* DS18B20_H */