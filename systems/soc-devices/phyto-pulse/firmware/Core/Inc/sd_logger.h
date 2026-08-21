/*
 * sd_logger.h — SD card logging (raw binary + event CSV)
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#ifndef SD_LOGGER_H
#define SD_LOGGER_H

#include <stdint.h>
#include <stdbool.h>
#include "spike_detect.h"
#include "slow_wave.h"

int sd_logger_init(void);

/* Start a new session — opens raw data file + events CSV */
int sd_logger_start_session(void);

/* Log a raw sample (24-bit voltage × 1000 → int16 mV) */
int sd_logger_log_sample(int32_t sample_idx, float voltage_mv, uint32_t timestamp_ms);

/* Log a detected event to CSV */
int sd_logger_log_event(const spike_event_t *event);

/* Log a slow-wave result */
int sd_logger_log_swp(const swp_result_t *result);

/* Stop session — flush and close files */
int sd_logger_stop_session(void);

/* Get SD card free space (MB) */
uint32_t sd_logger_free_mb(void);

/* Check if SD card is present */
bool sd_logger_card_present(void);

/* Get current session filename */
const char *sd_logger_session_filename(void);

#endif /* SD_LOGGER_H */