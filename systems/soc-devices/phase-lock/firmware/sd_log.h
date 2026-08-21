/*
 * sd_log.h — microSD card FAT32 CSV logging via SPI1
 */
#ifndef SD_LOG_H
#define SD_LOG_H

#include <stdint.h>
#include <stdbool.h>
#include "sweep.h"

void sd_log_init(void);
bool sd_log_ready(void);

/* Open a sweep log file: SWP_NNNN.csv (NNNN increments) */
void sd_log_open_sweep(uint16_t run_id);

/* Write a sweep point record */
void sd_log_sweep_point(const sweep_point_t *p);

/* Close the current log file */
void sd_log_close(void);

/* Open a time-trace log: TRC_NNNN.csv */
void sd_log_open_trace(uint16_t run_id, float freq, float tc_label);

/* Write a time-trace row (called at ~100 Hz) */
void sd_log_trace_row(uint32_t ts_ms, float R, float theta, float X, float Y, float noise);

#endif /* SD_LOG_H */