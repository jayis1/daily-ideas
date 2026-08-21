/*
 * pyro-balance / Core/Inc/sd_logger.h
 */
#ifndef SD_LOGGER_H
#define SD_LOGGER_H
#include "main.h"
void sd_init(void);
void sd_open_run(uint32_t method_id);
void sd_log_point(float temp_c, float mass_mg, float mass_pct, float dtg, uint32_t t_ms);
void sd_close_run(void);
void sd_log_event(const char* msg);
void sd_dump(const char* path, uint8_t* buf, uint32_t len);
bool sd_present(void);
#endif