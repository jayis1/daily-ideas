/**
 * lumen_cast/firmware/flashlog.h — W25Q128 flash scan logging
 */
#ifndef LUMEN_CAST_FLASHLOG_H
#define LUMEN_CAST_FLASHLOG_H

int flashlog_init(void);
float flashlog_load_cal_factor(void);
void flashlog_save_cal_factor(float factor);
int flashlog_write_scan(const photo_result_t *r, const scan_buffer_t *s);
int flashlog_read_scan(uint16_t id, photo_result_t *r);
uint16_t flashlog_get_count(void);

#endif