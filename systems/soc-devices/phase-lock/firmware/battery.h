/*
 * battery.h — battery voltage monitor + low-charge gating
 */
#ifndef BATTERY_H
#define BATTERY_H

float battery_read(void);          /* Volts  */
bool  battery_ok(void);             /* true if > 3.5 V */
bool  battery_low(void);            /* true if < 3.4 V */
#endif