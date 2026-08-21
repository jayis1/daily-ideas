/*
 * detector.h — ADS122U04 24-bit ADC + thermopile detector
 */

#ifndef DETECTOR_H
#define DETECTOR_H

#include <stdint.h>

typedef struct {
    float voltage_uv;     /* Thermopile voltage (µV) */
    float dni_wm2;        /* Direct Normal Irradiance (W/m²) */
    float temperature_c;  /* Detector temperature (°C, from cold junction) */
    uint8_t pga;          /* Current PGA setting */
} detector_reading_t;

/* Initialize ADS122U04 (SPI3) */
void detector_init(void);

/* Read one sample from the thermopile (blocking) */
void detector_read(detector_reading_t *reading);

/* Set PGA gain (1, 2, 4, 8, 16, 32, 64, 128) */
void detector_set_pga(uint8_t gain);

/* Average N readings for noise reduction */
void detector_read_avg(detector_reading_t *reading, uint8_t n);

/* Get calibration constants */
float detector_get_calibration(void);

/* Set calibration factor (V₀ per wavelength) */
void detector_set_calibration(float v0, uint8_t wl_index);

#endif /* DETECTOR_H */