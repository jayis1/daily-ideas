/*
 * sd_log.h — microSD CSV + raw binary electropherogram logging
 */

#ifndef SD_LOG_H
#define SD_LOG_H

#include "quant.h"

/* Initialize SD card (SPI1) */
void sd_log_init(void);

/* Write a complete run to SD card: CSV header + raw electropherogram binary */
void sd_log_write_run(uint16_t run_id, uint8_t bge_recipe, float hv_setpoint,
                      float hv_measured, float temp_c,
                      const float *eph, uint32_t eph_count,
                      const ion_result_t *results, uint8_t result_count);

/* Write an error log entry */
void sd_log_write_error(uint16_t run_id, const char *msg,
                        float current_ua, float voltage_kv);

#endif /* SD_LOG_H */