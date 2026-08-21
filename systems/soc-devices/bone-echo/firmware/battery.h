/*
 * battery.h — 18650 voltage monitor + low-charge gating
 */

#ifndef BATTERY_H
#define BATTERY_H

void  battery_init(void);
float battery_read(void);    /* Volts */
bool  battery_ok(void);      /* Vbat > 3.5 V */
bool  battery_low(void);     /* Vbat < 3.4 V */

#endif