/* flash_log.h — session logging to W25Q128 */
#ifndef FLASH_LOG_H
#define FLASH_LOG_H

typedef struct {
    uint32_t ts_ms;
    float    dew_c;
    float    rh_pct;
    float    ah_gm3;
    float    w_gkg;
    float    pressure_pa;
    uint16_t co2_ppm;
    float    mirror_c;
    float    tec_i;
    float    tec_v;
    int      phase;
    int      state;
} log_record_t;

void log_init(void);
void log_start(void);
void log_stop(void);
void log_append(const log_record_t *rec);
uint32_t log_session_id(void);

#endif