/*
 * kappa-pin / firmware / main / sd_logger.h
 * MicroSD FAT32 CSV + binary logging
 *
 * MIT License.
 */
#ifndef SD_LOGGER_H
#define SD_LOGGER_H

#include <stdint.h>
#include <stdbool.h>
#include "measurement.h"

/* SD card pins (shared SPI bus) */
#define SD_CS_PIN   18

typedef enum {
    SD_OK = 0,
    SD_ERR_MOUNT = -1,
    SD_ERR_OPEN = -2,
    SD_ERR_WRITE = -3,
    SD_ERR_NOTMOUNTED = -4,
} sd_err_t;

/* Initialize and mount SD card */
sd_err_t sd_logger_init(void);

/* Start a new measurement log file */
sd_err_t sd_logger_start(const meas_result_t *header_info, material_t mat);

/* Write a sample point */
sd_err_t sd_logger_write_sample(const meas_sample_t *s);

/* Write result summary at end */
sd_err_t sd_logger_write_result(const meas_result_t *r);

/* Close current log file */
sd_err_t sd_logger_close(void);

/* Check if SD card is mounted */
bool sd_logger_is_mounted(void);

/* Get last filename */
const char *sd_logger_last_filename(void);

#endif /* SD_LOGGER_H */