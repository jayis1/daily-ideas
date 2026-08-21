/*
 * onewire.h — DS18B20 1-Wire bit-banged driver
 */

#ifndef ONEWIRE_H
#define ONEWIRE_H

#include <stdint.h>

void onewire_init(void);
float onewire_read_temp_c(void);

#endif /* ONEWIRE_H */