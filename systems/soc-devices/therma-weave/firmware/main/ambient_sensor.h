/*
 * Therma Weave — Ambient Sensor
 * ambient_sensor.h — BME280 ambient temperature, humidity, pressure
 *
 * SPDX-License-Identifier: MIT
 */

#ifndef AMBIENT_SENSOR_H
#define AMBIENT_SENSOR_H

#include <stdint.h>
#include "driver/i2c.h"

#define BME280_ADDR         0x76

typedef struct {
    i2c_port_t i2c_num;
    float temperature;   /* °C */
    float humidity;      /* %RH */
    float pressure;      /* hPa */
    bool  initialized;
} ambient_sensor_t;

void ambient_sensor_init(ambient_sensor_t *as, i2c_port_t i2c_num);
void ambient_sensor_read(ambient_sensor_t *as);

#endif /* AMBIENT_SENSOR_H */