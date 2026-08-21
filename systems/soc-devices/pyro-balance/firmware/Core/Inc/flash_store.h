/*
 * pyro-balance / Core/Inc/flash_store.h
 * NV parameter storage (calibration + methods) using STM32 flash.
 */
#ifndef FLASH_STORE_H
#define FLASH_STORE_H
#include "main.h"

typedef struct {
    float    balance_scale;
    int32_t  balance_offset;
    float    ads_rtd_r0;          /* nominal PT1000 = 1000.0 */
    float    ads_rtd_a, ads_rtd_b;/* CVD coefficients */
    float    furnace_lag_c;       /* crucible-vs-furnace offset */
    uint16_t final_temp_c;
    uint16_t rate_c_per_min_x10;
    uint16_t hold_min;
    bool     purge_n2;
    uint32_t magic;               /* 0x5042414C 'PBAL' */
} flash_store_t;

extern flash_store_t g_cfg;

void  flash_load(void);
void  flash_save(void);
void  flash_defaults(void);

#endif