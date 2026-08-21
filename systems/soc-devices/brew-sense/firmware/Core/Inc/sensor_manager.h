/**
 * sensor_manager.h — Brew Sense Sensor Manager
 * 
 * Manages all sensor initialization, reading, and data aggregation
 * for the STM32L476RG-based fermentation monitor.
 */

#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <stdint.h>
#include <stdbool.h>

/* Sensor data structure — all readings in SI units */
typedef struct {
    float temperature_c;    /* DS18B20 reading in °C */
    float pressure_hpa;     /* BMP388 reading in hPa */
    float co2_ppm;          /* Senseair S8 reading in ppm */
    float ph;               /* EZO-pH reading */
    float gravity_sg;       /* Densitometer reading in SG (e.g. 1.050) */
    float battery_v;        /* Battery voltage in V */
    uint32_t timestamp_ms;  /* Reading timestamp */
} sensor_data_t;

/* Sensor status flags */
typedef enum {
    SENSOR_OK          = 0x00,
    SENSOR_DS18B20_ERR = 0x01,
    SENSOR_BMP388_ERR  = 0x02,
    SENSOR_S8_ERR      = 0x04,
    SENSOR_EZO_PH_ERR  = 0x08,
    SENSOR_DENS_ERR    = 0x10,
    SENSOR_BATT_LOW    = 0x20,
} sensor_status_t;

/* Sensor manager configuration */
typedef struct {
    uint32_t sample_interval_ms;   /* Default: 60000 (1 min) */
    bool enable_co2;                /* Enable S8 continuous mode */
    bool enable_ph;                 /* Enable EZO-pH */
    bool enable_gravity;            /* Enable densitometer */
    bool enable_pressure;           /* Enable BMP388 */
} sensor_config_t;

/**
 * Initialize all sensors and I/O buses.
 * Call once at startup.
 * @return SENSOR_OK on success, or bitmask of errors
 */
sensor_status_t sensor_manager_init(const sensor_config_t *config);

/**
 * Read all enabled sensors and populate the data structure.
 * @param data Pointer to sensor_data_t to fill
 * @return SENSOR_OK on success, or bitmask of errors
 */
sensor_status_t sensor_manager_read_all(sensor_data_t *data);

/**
 * Read temperature from DS18B20 only.
 * @return Temperature in °C, or -999.0 on error
 */
float ds18b20_read_temp(void);

/**
 * Read pressure from BMP388.
 * @return Pressure in hPa, or -1.0 on error
 */
float bmp388_read_pressure(void);

/**
 * Read CO₂ from Senseair S8.
 * @return CO₂ in ppm, or 0 on error
 */
uint16_t s8_read_co2(void);

/**
 * Read pH from EZO-pH module.
 * @return pH value (0.0-14.0), or -1.0 on error
 */
float ezo_ph_read(void);

/**
 * Start Senseair S8 continuous measurement mode.
 * The sensor will update its reading every 5 seconds.
 */
void s8_start_continuous(void);

/**
 * Stop Senseair S8 and put it in idle mode.
 */
void s8_stop_continuous(void);

/**
 * Calibrate EZO-pH with a known buffer.
 * @param ph_value The known pH of the calibration buffer
 * @return true if calibration was accepted
 */
bool ezo_ph_calibrate(float ph_value);

/**
 * Read battery voltage via ADC.
 * @return Voltage in V (0.0-6.0)
 */
float battery_read_voltage(void);

/**
 * De-initialize sensors and put them in low-power mode.
 */
void sensor_manager_sleep(void);

/**
 * Wake sensors from low-power mode.
 */
void sensor_manager_wake(void);

#endif /* SENSOR_MANAGER_H */