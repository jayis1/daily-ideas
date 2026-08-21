/*
 * Tremor Tile — Data Logger Header
 * data_logger.h
 */

#ifndef TREMOR_TILE_DATA_LOGGER_H
#define TREMOR_TILE_DATA_LOGGER_H

#include "fft_engine.h"
#include "env_sensor.h"
#include "anomaly_detect.h"
#include "sensor_acq.h"

void data_logger_init(void);
void data_logger_log_spectrum(spectral_features_t *features);
void data_logger_log_env(env_data_t *env);
void data_logger_log_raw(sample_batch_t *batch);
void data_logger_log_alert(alert_t *alert);

#endif // TREMOR_TILE_DATA_LOGGER_H