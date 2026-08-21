/*
 * sd_log.h — SD card CSV + binary session logging
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef SD_LOG_H
#define SD_LOG_H

#include "ims.h"
#include "library.h"
#include <stdbool.h>

void sdlog_init(void);
bool sdlog_open_session(void);
void sdlog_log_spectrum(const ims_result_t *r, const classify_result_t *cls);
void sdlog_close_session(void);
bool sdlog_ready(void);

#endif /* SD_LOG_H */