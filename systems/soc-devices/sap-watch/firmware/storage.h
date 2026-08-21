/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * storage.h — Flash storage interface for config + log
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SAP_WATCH_STORAGE_H
#define SAP_WATCH_STORAGE_H

#include <stdint.h>

typedef struct {
    uint16_t timestamp_min;    /* minutes since boot */
    float    sap_flux_cmh;     /* sap-flux velocity */
    float    sapwood_temp;     /* °C */
    float    air_temp;         /* °C */
    float    humidity;         /* %RH */
    uint8_t  battery_pct;     /* % */
    uint8_t  flags;           /* bitfield */
} log_entry_t;

int     storage_init(void);
int     storage_save_config(void);
int     storage_get_credentials(uint8_t *deveui, uint8_t *appeui, uint8_t *appkey);
int     storage_set_credentials(const uint8_t *deveui, const uint8_t *appeui,
                                 const uint8_t *appkey);
float   storage_get_sapwood_area(void);
float   storage_get_wound_factor(void);
float   storage_get_k_xylem(void);
uint16_t storage_get_interval(void);
void    storage_set_sapwood_area(float a);
void    storage_set_wound_factor(float f);
void    storage_set_interval(uint16_t min);
int     storage_log_add(const log_entry_t *entry);
int     storage_log_count(void);

#endif /* SAP_WATCH_STORAGE_H */