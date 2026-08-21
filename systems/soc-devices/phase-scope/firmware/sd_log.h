/*
 * Phase Scope — SD Logger header
 */

#ifndef SD_LOG_H
#define SD_LOG_H

#include "power_quality.h"

int sd_log_init(void);
void sd_log_start(void);
void sd_log_stop(void);
void sd_log_write(const power_results_t *res);

#endif /* SD_LOG_H */