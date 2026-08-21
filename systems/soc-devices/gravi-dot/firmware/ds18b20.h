/** ds18b20.h — 4× DS18B20 1-Wire temperature array */
#ifndef DS18B20_H
#define DS18B20_H
#include <stdint.h>
void ds18b20_read_all(float temps[4]);
#endif