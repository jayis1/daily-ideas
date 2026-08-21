/*
 * temperature.h — DS18B20 1-Wire temperature sensor driver
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Used for temperature compensation of specific rotation.
 * Connected on PC0 (1-Wire data line with 4.7kΩ pullup to 3.3V).
 */
#ifndef TEMPERATURE_H
#define TEMPERATURE_H

void temperature_init(void);
double temperature_read(void);          /* returns Celsius */
uint8_t temperature_is_present(void);   /* sensor detected? */

#endif /* TEMPERATURE_H */