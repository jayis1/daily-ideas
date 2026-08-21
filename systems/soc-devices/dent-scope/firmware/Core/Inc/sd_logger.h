/*
 * dent-scope / Core/Inc/sd_logger.h
 * Dent Scope — SD card FATFS logging
 * MIT License.
 */
#ifndef SD_LOGGER_H
#define SD_LOGGER_H

#include "main.h"

void sd_init(void);
void sd_open_run(uint32_t run_id);
void sd_log_point(float force_mN, float depth_um, int state, uint32_t t_ms);
void sd_close_run(void);

#endif /* SD_LOGGER_H */