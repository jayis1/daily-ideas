/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * water_quality.h — DS18B20, MS5837, Atlas DO, BME280 drivers
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef WATER_QUALITY_H
#define WATER_QUALITY_H

#include "config.h"

/* Initialize all water-quality sensors */
int water_quality_init(void);

/* Read water temperature from DS18B20 (°C). Returns -999.0 on error. */
float water_temp_read_c(void);

/* Read dissolved oxygen from Atlas Scientific DO EZO (mg/L). Returns -1.0 on error. */
float water_do_read_mgl(void);

/* Read water depth from MS5837 (meters, relative to deployment datum).
 * Uses BME280 barometric pressure for atmospheric compensation.
 * Returns -999.0 on error. */
float water_depth_read_m(float baro_hpa);

/* Read barometric pressure from BME280 (hPa). Returns -1.0 on error. */
float baro_read_hpa(void);

/* Read all water-quality parameters into state struct */
void water_quality_sample_all(mussel_watch_state_t *st);

/* Convert MS5837 raw D1/D2 to pressure (mbar) and temperature (°C) */
void ms5837_convert(const uint16_t prom[8], uint32_t d1, uint32_t d2,
                    float *pressure_mbar, float *temp_c);

#endif /* WATER_QUALITY_H */