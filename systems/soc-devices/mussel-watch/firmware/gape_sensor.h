/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * gape_sensor.h — DRV5053 Hall sensor + ADS1115 ADC driver, gape-angle conversion
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef GAPE_SENSOR_H
#define GAPE_SENSOR_H

#include "config.h"

/* Initialize the TCA9548A I²C multiplexer and all ADS1115 channels */
int gape_sensor_init(void);

/* Select a channel (0–3) on the TCA9548A mux */
int gape_mux_select(uint8_t channel);

/* Read raw ADS1115 conversion result for a given channel (0–3)
 * Returns the Hall voltage in millivolts (single-ended AIN0 vs GND) */
float gape_read_hall_mv(uint8_t channel);

/* Convert Hall voltage to gape angle using stored calibration
 * Returns angle in degrees (0 = closed, up to GAPE_MAX_ANGLE_DEG = open)
 * Returns -1.0 if calibration is not valid */
float gape_hall_to_angle(uint8_t channel, float hall_mv);

/* Set calibration points (called from BLE or button handler) */
void gape_calibrate_closed(uint8_t channel);
void gape_calibrate_open(uint8_t channel);

/* Sample all active mussel heads, store results in state->gape_angle[] */
void gape_sample_all(mussel_watch_state_t *st);

/* Persist calibration to nRF flash (non-volatile) */
int gape_cal_save(const mussel_watch_state_t *st);
int gape_cal_load(mussel_watch_state_t *st);

#endif /* GAPE_SENSOR_H */