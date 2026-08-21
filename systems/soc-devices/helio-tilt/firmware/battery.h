/*
 * battery.h — 18650 battery voltage monitor
 */

#ifndef BATTERY_H
#define BATTERY_H

/* Initialize ADC1 channel for battery monitoring (PA0) */
void battery_init(void);

/* Read battery voltage (volts) */
float battery_read(void);

/* Check if battery is low */
int battery_low(void);

#endif /* BATTERY_H */