/*
 * Pulse Hound — RF Signal Hunter
 * sd_logger.h — SD card logging interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_SD_LOGGER_H
#define PULSE_HOUND_SD_LOGGER_H

#include <stdint.h>

typedef struct {
    int initialized;
    int card_present;
    int logging;
    uint32_t elapsed_ms;
} sd_logger_status_t;

int  sd_logger_init(void);
int  sd_logger_is_present(void);
int  sd_logger_start(const char *filename);
void sd_logger_stop(void);
int  sd_logger_is_logging(void);
void sd_logger_write(float rssi_dbm, float peak_rssi, int classification,
                     float bearing_deg, int battery_pct, int mode);
void sd_logger_flush(void);
int  sd_logger_get_status(sd_logger_status_t *status);

#endif /* PULSE_HOUND_SD_LOGGER_H */