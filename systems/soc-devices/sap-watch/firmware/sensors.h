/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * sensors.h — Environmental sensor interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SAP_WATCH_SENSORS_H
#define SAP_WATCH_SENSORS_H

#include <stdint.h>
#include <math.h>

typedef struct {
    float air_temp_c;       /* SHT45 air temperature (°C) */
    float rh_pct;            /* SHT45 relative humidity (%) */
    float light_lux;         /* TSL2591 ambient light (lux) */
    float sapwood_temp_c;    /* DS18B20 sapwood temperature (°C) */
    float vpd_kpa;           /* computed vapor pressure deficit (kPa) */
    float battery_pct;       /* MAX17048 state of charge (%) */
    float battery_v;         /* MAX17048 battery voltage (V) */
} sensor_data_t;

/* Individual sensor reads */
int sht45_read(float *temp_c, float *rh_pct);
int tsl2591_init(void);
int tsl2591_read(float *lux);
int ds18b20_read(float *temp_c);
int max17048_init(void);
int max17048_read_soc(float *percent);
int max17048_read_voltage(float *volts);

/* Read all sensors into a sensor_data_t struct. Returns 0 on success. */
int sensors_read_all(sensor_data_t *data);

#endif /* SAP_WATCH_SENSORS_H */