/*
 * Hive Mind — Weight Sensor Driver Header
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef WEIGHT_SENSOR_H
#define WEIGHT_SENSOR_H

#include <stdint.h>

void weight_sensor_init(void);
void weight_sensor_tare(void);
float weight_sensor_read_grams(void);
void weight_sensor_set_calibration(float known_weight_grams);
void weight_sensor_power_off(void);
void weight_sensor_power_on(void);

#endif /* WEIGHT_SENSOR_H */