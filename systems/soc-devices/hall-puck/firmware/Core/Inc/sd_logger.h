/*
 * hall-puck / firmware / Core / Inc / sd_logger.h
 * MicroSD FAT32 CSV logging
 *
 * MIT License.
 */
#ifndef SD_LOGGER_H
#define SD_LOGGER_H

#include <stdint.h>
#include <stdbool.h>
#include "measurement.h"

typedef enum {
    SD_OK = 0,
    SD_ERR_MOUNT = -1,
    SD_ERR_OPEN = -2,
    SD_ERR_WRITE = -3,
    SD_ERR_NOTMOUNTED = -4,
} sd_err_t;

sd_err_t sd_logger_init(void);
sd_err_t sd_logger_start(const meas_result_t *header, const meas_params_t *params);
sd_err_t sd_logger_write_point(const meas_point_t *p, int idx);
sd_err_t sd_logger_write_result(const meas_result_t *r);
sd_err_t sd_logger_close(void);
bool sd_logger_is_mounted(void);
const char *sd_logger_last_filename(void);

#endif /* SD_LOGGER_H */