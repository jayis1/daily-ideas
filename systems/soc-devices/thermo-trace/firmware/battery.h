/*
 * battery.h — LiPo battery monitoring (header)
 */
#ifndef BATTERY_H
#define BATTERY_H

#include <stdint.h>

void    battery_init(void);
uint8_t battery_percent(void);
float   battery_voltage(void);
bool    battery_is_charging(void);

#endif /* BATTERY_H */