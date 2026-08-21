/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * anomaly.h — Closure-event detection, rhythm analysis, stress scoring
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef ANOMALY_H
#define ANOMALY_H

#include "config.h"

/* Initialize the anomaly detection subsystem */
void anomaly_init(mussel_watch_state_t *st);

/* Process a new gape sample (called at the sample rate).
 * Updates closure-event counters, checks for sustained closure,
 * rhythm deviation, and multi-mussel events.
 * Returns the alert_code_t if a new alert is triggered, ALERT_NONE otherwise. */
alert_code_t anomaly_update(mussel_watch_state_t *st, uint32_t now_ms);

/* Check water-quality parameters for anomalies (temperature spikes, hypoxia) */
alert_code_t anomaly_check_water_quality(mussel_watch_state_t *st);

/* Get a human-readable description for an alert code */
const char *anomaly_alert_name(alert_code_t code);

/* Reset hourly closure-event counters (called when the hour rolls over) */
void anomaly_reset_hourly(mussel_watch_state_t *st);

/* Update the 24-hour rhythm profile (call once per uplink) */
void anomaly_update_rhythm(mussel_watch_state_t *st, uint32_t now_ms);

#endif /* ANOMALY_H */