/*
 * power.h — battery, rails, charging
 */

#ifndef POWER_H
#define POWER_H

#include <stdint.h>

void power_init(void);
float power_read_battery_mv(void);
uint8_t power_is_charging(void);
uint8_t power_battery_pct(void);

#endif /* POWER_H */