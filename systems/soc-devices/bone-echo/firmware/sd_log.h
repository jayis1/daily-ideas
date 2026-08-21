/*
 * sd_log.h — microSD CSV + raw waveform binary logging
 */

#ifndef SD_LOG_H
#define SD_LOG_H

#include <stdint.h>

void sd_log_init(void);
void sd_log_open_scan(uint16_t id, uint16_t patient_id, uint8_t age,
                      uint8_t sex, uint8_t eth);
void sd_log_results(uint16_t id, float sos, float bua, float si,
                     float t, float z, int cls);
void sd_log_waveform(uint16_t id, const uint16_t *buf, uint32_t n);
void sd_log_close(void);

#endif