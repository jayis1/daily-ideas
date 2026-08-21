/*
 * battery.h — 18650 battery voltage monitor
 */

#ifndef BATTERY_H
#define BATTERY_H

#include <stdbool.h>

void   battery_init(void);
float  battery_read(void);    /* volts */
bool   battery_ok(void);      /* > 3.4 V */
bool   battery_low(void);     /* < 3.4 V */

#endif /* BATTERY_H */