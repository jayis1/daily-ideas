/*
 * dent-scope / Core/Inc/ds18b20.h
 * Dent Scope — DS18B20 1-wire temperature sensor
 * MIT License.
 */
#ifndef DS18B20_H
#define DS18B20_H

#include "main.h"

void  ds18b20_init(void);
float ds18b20_read_temp(void);

#endif /* DS18B20_H */