/*
 * sd_log.h — microSD SPI logging (header)
 */
#ifndef SD_LOG_H
#define SD_LOG_H

#include <stdint.h>
#include <stdbool.h>

void    sd_init(void);
bool    sd_mount(void);
void    sd_open_session(uint32_t timestamp);
void    sd_log_point(float temp, float heat_flow, float time, float setpoint);
void    sd_close_session(void);
bool    sd_is_present(void);
void    sd_write_string(const char *str);

#endif /* SD_LOG_H */