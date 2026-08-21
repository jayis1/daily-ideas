/*
 * sd_log.h — SD card logging and library persistence
 * Opti Rot — Pocket Digital Polarimeter
 */
#ifndef SD_LOG_H
#define SD_LOG_H

#include <stdint.h>
#include "library.h"

void sd_log_init(void);

/* Append a measurement to the CSV log */
void sd_log_measurement(double rotation, double concentration,
                         const char *compound, double confidence,
                         double temperature, double wavelength);

/* Save/load custom library entries */
void sd_log_save_library(const library_entry_t *entries, int count);
void sd_log_load_library(library_entry_t *entries, int max, int *count);

#endif /* SD_LOG_H */