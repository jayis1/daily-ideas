/* sd_log.h — microSD card CSV logging via SPI */

#ifndef SD_LOG_H
#define SD_LOG_H

#include <stdint.h>
#include <stdbool.h>
#include "sonic.h"
#include "wind.h"
#include "bme280.h"

typedef enum {
    LOG_FMT_FULL,    /* 20 Hz raw wind + atmospheric */
    LOG_FMT_AVERAGE, /* averaged statistics */
    LOG_FMT_FLUX,    /* turbulence flux data */
} log_format_t;

bool sd_init(void);

/* Open a new log file with timestamp name */
bool sd_open_log(void);

/* Log a raw wind sample */
void sd_log_wind(const sonic_sample_t *sonic, const wind_vector_t *wind,
                 const bme280_data_t *atm);

/* Log turbulence statistics */
void sd_log_turbulence(const turbulence_stats_t *stats, uint32_t elapsed_s);

/* Flush and close */
void sd_close_log(void);

/* Check if SD card is present */
bool sd_present(void);

#endif /* SD_LOG_H */