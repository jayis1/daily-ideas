/*
 * Tremor Tile — Environment Sensor Header
 * env_sensor.h
 */

#ifndef TREMOR_TILE_ENV_SENSOR_H
#define TREMOR_TILE_ENV_SENSOR_H

typedef struct {
    float temperature;    // Degrees Celsius
    float humidity;       // Percent RH
    float pressure;       // Hectopascals (hPa)
} env_data_t;

void env_sensor_init(void);
env_data_t env_sensor_read(void);

#endif // TREMOR_TILE_ENV_SENSOR_H