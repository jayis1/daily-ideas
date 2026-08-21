/*
 * pyro-balance / Core/Src/flash_store.c — NV parameter storage.
 * Uses last page of STM32G474 flash (page 127, 0x0807F800, 2KB).
 */
#include "flash_store.h"

flash_store_t g_cfg;

#define FLASH_PAGE_ADDR 0x0807F800U

void flash_defaults(void) {
    g_cfg.balance_scale = 0.00015f;       /* mg/count; calibrate */
    g_cfg.balance_offset = 0;
    g_cfg.ads_rtd_r0 = 1000.0f;
    g_cfg.ads_rtd_a = 3.9083e-3f;
    g_cfg.ads_rtd_b = -5.775e-7f;
    g_cfg.furnace_lag_c = 0.0f;
    g_cfg.final_temp_c = 600;
    g_cfg.rate_c_per_min_x10 = 100;       /* 10 °C/min */
    g_cfg.hold_min = 5;
    g_cfg.purge_n2 = false;
    g_cfg.magic = 0x5042414C;
    flash_save();
}

void flash_load(void) {
    flash_store_t* stored = (flash_store_t*)FLASH_PAGE_ADDR;
    if (stored->magic == 0x5042414C) {
        memcpy(&g_cfg, stored, sizeof(g_cfg));
    } else {
        flash_defaults();
    }
}

void flash_save(void) {
    HAL_FLASH_Unlock();
    FLASH_EraseInitTypeDef e = {0};
    e.TypeErase = FLASH_TYPEERASE_PAGES;
    e.Page = 127;
    e.NbPages = 1;
    e.Banks = FLASH_BANK_1;
    uint32_t err;
    HAL_FLASHEx_Erase(&e, &err);
    uint64_t* src = (uint64_t*)&g_cfg;
    uint32_t addr = FLASH_PAGE_ADDR;
    for (uint32_t i = 0; i < sizeof(g_cfg)/8; i++) {
        HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, addr, src[i]);
        addr += 8;
    }
    HAL_FLASH_Lock();
}