/*
 * sd_log.h — microSD CSV logging for particle counter
 */

#ifndef SD_LOG_H
#define SD_LOG_H

#include <stdint.h>

void   sd_log_init(void);
void   sd_log_minute(uint16_t id, float dt_s, float vol_l, float flow_lpm,
                      float temp_c, float rh_pct, float pres_hpa,
                      const uint32_t *counts, uint8_t n,
                      float pm1, float pm25, float pm10);
void   sd_log_flush(void);

#endif /* SD_LOG_H */