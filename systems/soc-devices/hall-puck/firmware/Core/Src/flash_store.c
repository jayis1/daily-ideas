/*
 * hall-puck / firmware / Core / Src / flash_store.c
 * Flash-based persistent storage (emulated EEPROM)
 *
 * Uses STM32G474 flash sector 62 (last 2KB of flash) for config.
 * Simple read/write with wear-leveling (single sector, ~10k writes).
 *
 * MIT License.
 */
#include "flash_store.h"
#include "main.h"
#include <string.h>

/* Use last flash page (page 127 = 0x0807F800 for 512KB flash) */
#define FLASH_CONFIG_ADDR   0x0807F800
#define FLASH_CONFIG_SECTOR 127
#define FLASH_MAGIC         0x48414C50  /* "HALP" */

static flash_config_t config;

static const flash_config_t default_config = {
    .b_field_calibration = MAGNETIC_FIELD_T,  /* 0.482 T */
    .current_calibration = 1.0f,
    .voltage_offset_uv = 0.0f,
    .sample_thickness_mm = 0.5f,
    .measurement_current_ma = 1.0f,
    .last_mode = 0,
    .cal_timestamp = 0,
    .total_measurements = 0,
};

void flash_store_init(void)
{
    /* Read config from flash */
    flash_config_t *flash_cfg = (flash_config_t *)FLASH_CONFIG_ADDR;

    /* Check magic number */
    uint32_t magic;
    memcpy(&magic, flash_cfg, sizeof(magic));

    if (magic == FLASH_MAGIC) {
        /* Valid config exists — copy to RAM */
        memcpy(&config, flash_cfg, sizeof(config));
    } else {
        /* No valid config — use defaults */
        config = default_config;
        flash_store_save(&config);
    }
}

const flash_config_t *flash_store_get(void)
{
    return &config;
}

void flash_store_save(const flash_config_t *cfg)
{
    /* Unlock flash */
    FLASH->KEYR = 0x45670123;
    FLASH->KEYR = 0xCDEF89AB;

    /* Erase page */
    FLASH->CR |= FLASH_CR_PER;
    FLASH->CR &= ~FLASH_CR_PNB;
    FLASH->CR |= (FLASH_CONFIG_SECTOR << FLASH_CR_PNB_Pos);
    FLASH->AR = FLASH_CONFIG_ADDR;
    FLASH->CR |= FLASH_CR_STRT;

    while (FLASH->SR & FLASH_SR_BSY);

    /* Write config (32-bit words) */
    FLASH->CR &= ~FLASH_CR_PER;
    FLASH->CR |= FLASH_CR_PG;

    /* Write magic + config as 32-bit words */
    uint32_t *dst = (uint32_t *)FLASH_CONFIG_ADDR;
    uint32_t *src = (uint32_t *)cfg;

    /* First write magic */
    *dst = FLASH_MAGIC;
    while (FLASH->SR & FLASH_SR_BSY);

    /* Then write config data */
    int n_words = (sizeof(flash_config_t) + 3) / 4;
    for (int i = 0; i < n_words; i++) {
        dst[i + 1] = src[i];
        while (FLASH->SR & FLASH_SR_BSY);
    }

    /* Lock flash */
    FLASH->CR &= ~FLASH_CR_PG;
    FLASH->CR |= FLASH_CR_LOCK;

    /* Update RAM copy */
    config = *cfg;
}

void flash_store_set_b_calibration(float b_t)
{
    config.b_field_calibration = b_t;
    flash_store_save(&config);
}

void flash_store_set_current_calibration(float cf)
{
    config.current_calibration = cf;
    flash_store_save(&config);
}

void flash_store_set_voltage_offset(float offset_uv)
{
    config.voltage_offset_uv = offset_uv;
    flash_store_save(&config);
}

void flash_store_set_thickness(float mm)
{
    config.sample_thickness_mm = mm;
    flash_store_save(&config);
}

void flash_store_set_current(float ma)
{
    config.measurement_current_ma = ma;
    flash_store_save(&config);
}

void flash_store_increment_measurements(void)
{
    config.total_measurements++;
    /* Don't save every time (wear) — save every 10 measurements */
    if (config.total_measurements % 10 == 0) {
        flash_store_save(&config);
    }
}

void flash_store_reset(void)
{
    config = default_config;
    flash_store_save(&config);
}