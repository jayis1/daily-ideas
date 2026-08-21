/*
 * Tremor Tile — Anomaly Detection Header
 * anomaly_detect.h
 */

#ifndef TREMOR_TILE_ANOMALY_DETECT_H
#define TREMOR_TILE_ANOMALY_DETECT_H

#include <stdint.h>
#include <stdbool.h>
#include "fft_engine.h"

// Alert structure (sent over LoRa)
typedef struct {
    uint8_t type;            // ALERT_NEW_PEAK, ALERT_PEAK_SHIFT, etc.
    uint8_t severity;         // 1-10 scale
    uint16_t affected_bands;  // Bitmask of affected frequency bands
    int64_t timestamp;        // Unix timestamp from RTC
} alert_t;

// Anomaly evaluation result
typedef struct {
    bool is_anomaly;
    uint8_t type;
    uint8_t severity;
    uint16_t affected_bands;
    int64_t timestamp;
} anomaly_result_t;

// Initialize anomaly detection (load or start baseline learning)
void anomaly_detect_init(void);

// Evaluate current features against baseline
anomaly_result_t anomaly_detect_evaluate(spectral_features_t *features);

// Flag an alert for Core 0 to transmit
void anomaly_detect_flag_alert(anomaly_result_t *result);

// Check if an alert is pending
bool anomaly_detect_alert_pending(void);

// Get the pending alert
alert_t anomaly_detect_get_alert(void);

// Reset baseline (restart learning)
void anomaly_detect_reset_baseline(void);

// Set anomaly threshold (sigma multiplier)
void anomaly_detect_set_threshold(float sigma);

#endif // TREMOR_TILE_ANOMALY_DETECT_H