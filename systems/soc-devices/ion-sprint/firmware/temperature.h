/*
 * temperature.h — DS18B20 BGE temperature reading + mobility correction
 */

#ifndef TEMPERATURE_H
#define TEMPERATURE_H

/* Initialize DS18B20 on 1-Wire (PC6) */
void temperature_init(void);

/* Read current BGE temperature in °C */
float temperature_read(void);

/* Compute mobility temperature correction factor:
 * μ(T) = μ(25°C) × [1 + α·(T-25)], α = 0.02 /°C
 */
float temperature_mobility_correction(float temp_c);

#endif /* TEMPERATURE_H */