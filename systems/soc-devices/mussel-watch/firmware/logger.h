/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * logger.h — SD card FAT32 logging
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef LOGGER_H
#define LOGGER_H

#include "config.h"

/* Initialize the SD card and FAT32 filesystem */
int logger_init(void);

/* Append a CSV log line with the current state */
int logger_log(const mussel_watch_state_t *st, uint32_t timestamp_s);

/* Log a calibration event */
int logger_log_calibration(const mussel_watch_state_t *st, int channel, const char *event);

/* Log an alert event */
int logger_log_alert(const mussel_watch_state_t *st, alert_code_t code, uint32_t timestamp_s);

/* Get the current log file name (YYYY-MM-DD.csv format) */
void logger_get_filename(char *buf, int len, uint32_t timestamp_s);

/* Mount/unmount the SD card */
int logger_mount(void);
int logger_unmount(void);

#endif /* LOGGER_H */