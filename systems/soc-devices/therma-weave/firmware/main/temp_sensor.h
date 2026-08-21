/*
 * Therma Weave — Temperature Sensor
 * temp_sensor.h — 74HC4051 multiplexed NTC thermistor reading
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef TEMP_SENSOR_H
#define TEMP_SENSOR_H

#include <stdint.h>
#include <stdbool.h>

#define NUM_THERMISTORS  8    /* 8 channels on 74HC4051 */
#define NUM_ZONES        4    /* 2 thermistors per zone */
#define BETA            3950  /* NTC beta coefficient */
#define R_NOMINAL       10000 /* NTC resistance at 25°C (10kΩ) */
#define T_NOMINAL       298.15f /* 25°C in Kelvin */
#define R_SERIES        10000 /* Series resistor in voltage divider */

typedef struct {
    /* GPIO pins for 74HC4051 select */
    uint8_t mux_a_pin;
    uint8_t mux_b_pin;
    uint8_t mux_c_pin;
    uint8_t mux_en_pin;

    /* Raw ADC readings (0-4095 for ESP32-C3 12-bit ADC) */
    uint16_t raw_adc[NUM_THERMISTORS];

    /* Converted temperatures (°C) */
    float temp_c[NUM_THERMISTORS];

    /* Zone temperatures (averaged from 2 thermistors each) */
    float zone_temp[NUM_ZONES];

    /* Fault flags per thermistor */
    bool open_circuit[NUM_THERMISTORS];
    bool short_circuit[NUM_THERMISTORS];
} temp_sensor_t;

/**
 * Initialize the temperature sensor subsystem.
 * Sets up 74HC4051 select pins and ADC.
 */
void temp_sensor_init(temp_sensor_t *ts, uint8_t mux_a, uint8_t mux_b,
                       uint8_t mux_c, uint8_t mux_en);

/**
 * Scan all 8 thermistor channels through the 74HC4051 mux.
 * Updates raw_adc[] and temp_c[] arrays.
 */
void temp_sensor_scan_all(temp_sensor_t *ts);

/**
 * Get the averaged temperature for a specific zone.
 * Zone 0 uses channels 0,1; Zone 1 uses channels 2,3; etc.
 */
float temp_sensor_get_zone_temp(temp_sensor_t *ts, uint8_t zone);

/**
 * Convert raw ADC value to NTC thermistor resistance.
 */
float temp_sensor_adc_to_resistance(uint16_t adc_val);

/**
 * Convert NTC thermistor resistance to temperature using
 * simplified Steinhart-Hart equation.
 */
float temp_sensor_resistance_to_temp(float resistance);

#endif /* TEMP_SENSOR_H */