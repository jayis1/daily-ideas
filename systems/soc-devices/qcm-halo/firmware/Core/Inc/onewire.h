/*
 * onewire.h — DS18B20 1-Wire interface
 */

#ifndef ONEWIRE_H
#define ONEWIRE_H

#include "config.h"

int  onewire_init(void);
int  onewire_reset(void);
void onewire_write_byte(uint8_t byte);
uint8_t onewire_read_byte(void);

float ds18b20_read_temp(void);  /* °C, returns -999 on error */

#endif /* ONEWIRE_H */