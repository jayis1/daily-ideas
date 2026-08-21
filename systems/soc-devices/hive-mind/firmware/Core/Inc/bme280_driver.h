/*
 * Hive Mind — BME280 Driver Header
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef BME280_DRIVER_H
#define BME280_DRIVER_H

void bme280_init(void);
void bme280_read(float *temperature, float *humidity, float *pressure);

#endif /* BME280_DRIVER_H */