/*
 * Pulse Hound — RF Signal Hunter
 * rf_detector.h — RF detector interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_RF_DETECTOR_H
#define PULSE_HOUND_RF_DETECTOR_H

#include <stdint.h>

/* Power management */
void rf_detector_power_on(void);
void rf_detector_power_off(void);
int  rf_detector_is_powered(void);

/* RSSI measurement (returns dBm) */
int  rf_detector_read_rssi_dbm(float *rssi_dbm);

/* Bulk sampling */
int  rf_detector_sample_burst(float *samples, int count, uint32_t sample_interval_ms);

/* Temperature (for compensation) */
float rf_detector_read_temp_c(void);

/* Calibration */
void rf_detector_set_calibration(float slope, float intercept, float temp_coeff);
void rf_detector_get_calibration(float *slope, float *intercept, float *temp_coeff);

/* Statistics */
float rf_detector_median_rssi(float *samples, int count);

#endif /* PULSE_HOUND_RF_DETECTOR_H */