/*
 * visco-shear / firmware / sd_logger.h
 */
#ifndef VISCO_SHEAR_SD_LOGGER_H
#define VISCO_SHEAR_SD_LOGGER_H

#include "main.h"

void sd_logger_init(void);
void sd_logger_write_result(const measure_result_t *res);
void sd_logger_write_osc(const measure_result_t *res);

#endif