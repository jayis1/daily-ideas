/*
 * bme280.h — BME280 temperature/humidity/pressure sensor
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#ifndef BME280_H
#define BME280_H

#include <stdint.h>

typedef struct {
    float temperature;  /* °C */
    float humidity;     /* % */
    float pressure;     /* hPa */
} bme280_data_t;

int bme280_init(void);
int bme280_read(bme280_data_t *data);

#endif /* BME280_H */