/*
 * Hive Mind — Hive Health Header
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef HIVE_HEALTH_H
#define HIVE_HEALTH_H

#include "oled_display.h"  /* for sensor_data_t */

float hive_health_compute(const sensor_data_t *data);
const char *hive_health_label(float score);

#endif /* HIVE_HEALTH_H */