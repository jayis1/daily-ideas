/*
 * dent-scope / Core/Src/flash_store.c
 * Dent Scope — NV flash parameter storage (STM32G4 flash page)
 * MIT License.
 */
#include "flash_store.h"

#define FLASH_CONFIG_ADDR  0x08060000  /* page 96 (last 4KB page in 128KB flash) */
#define FLASH_CONFIG_MAGIC 0x44454E54   /* "DENT" */

void flash_load(void)
{
    ds_config_t *stored = (ds_config_t *)FLASH_CONFIG_ADDR;
    if (stored->magic == FLASH_CONFIG_MAGIC) {
        memcpy(&g_cfg, stored, sizeof(g_cfg));
    } else {
        flash_defaults();
    }
}

void flash_save(void)
{
    HAL_FLASH_Unlock();
    FLASH_EraseInitTypeDef erase = {0};
    erase.TypeErase = FLASH_TYPEERASE_PAGES;
    erase.Page = 96;
    erase.NbPages = 1;
    uint32_t err;
    HAL_FLASHEx_Erase(&erase, &err);

    g_cfg.magic = FLASH_CONFIG_MAGIC;
    uint64_t *src = (uint64_t *)&g_cfg;
    for (int i = 0; i < (int)(sizeof(ds_config_t) / 8); i++) {
        HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD,
                         FLASH_CONFIG_ADDR + i * 8, src[i]);
    }
    HAL_FLASH_Lock();
}

void flash_defaults(void)
{
    memset(&g_cfg, 0, sizeof(g_cfg));
    g_cfg.magic = FLASH_CONFIG_MAGIC;
    g_cfg.hx711_offset = 0.0f;
    g_cfg.hx711_scale = 0.00244f;     /* approx: 20N × 1000 mN/N / (8388608 counts) */
    g_cfg.cap_offset = 0.0f;
    g_cfg.cap_scale = 11.0f;          /* approx: µm per pF (calibrate with gauge blocks) */
    g_cfg.cap_quad = 0.0f;
    g_cfg.tip = TIP_VICKERS;
    g_cfg.target_force_N = 10.0f;
    g_cfg.loading_rate_Ns = 1.0f;
    g_cfg.hold_time_s = 5.0f;
    g_cfg.poisson = 0.30f;            /* default steel */
    flash_save();
}