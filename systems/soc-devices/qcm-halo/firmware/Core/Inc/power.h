/*
 * power.h — Battery monitoring and power management
 */

#ifndef POWER_H
#define POWER_H

#include "config.h"

float power_read_battery_mv(void);
uint8_t power_get_battery_pct(void);
uint8_t power_is_charging(void);
uint8_t power_is_low(void);

void power_enter_lowpower(void);
void power_wakeup(void);

#endif /* POWER_H */