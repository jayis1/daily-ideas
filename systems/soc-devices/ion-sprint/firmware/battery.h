/*
 * battery.h — 18650 voltage monitor + low-charge gating
 */

#ifndef BATTERY_H
#define BATTERY_H

#include <stdbool.h>

/* Initialize battery monitor (PA4 ADC1_IN17, 2:1 divider) */
void battery_init(void);

/* Read battery voltage (V) */
float battery_read(void);

/* Check if battery is OK for HV operation (> 3.5 V) */
bool battery_ok(void);

/* Check if battery is low (< 3.4 V) */
bool battery_low(void);

#endif /* BATTERY_H */