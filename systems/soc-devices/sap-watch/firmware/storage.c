/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * storage.c — Flash-backed configuration and measurement log ring buffer
 *             (NVRAM emulation in STM32WL flash)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "storage.h"
#include <string.h>

/* ---- Platform flash stubs ---- */
extern int  flash_write(uint32_t addr, const uint8_t *data, uint16_t len);
extern int  flash_read(uint32_t addr, uint8_t *data, uint16_t len);
extern int  flash_erase_sector(uint32_t sector_addr);

/* Flash layout (in the last 2 pages of STM32WL55 flash, 256 KB total):
 *   0x0803F000 — config page (4 KB)
 *   0x0803E000 — log ring buffer (4 KB, 256 entries × 16 bytes)
 */

#define FLASH_CONFIG_ADDR    0x0803F000U
#define FLASH_LOG_ADDR       0x0803E000U
#define LOG_ENTRY_BYTES      16
#define LOG_MAX_ENTRIES      256

/* Config structure stored in flash */
typedef struct {
    uint32_t magic;
    uint16_t measurement_interval_min;
    float    sapwood_area_cm2;
    float    wound_factor;
    float    k_xylem;
    float    zero_flow_offset;
    uint8_t  zero_cal_valid;
    uint8_t  reserved[3];
    uint8_t  dev_eui[8];
    uint8_t  app_eui[8];
    uint8_t  app_key[16];
    uint32_t crc;
} config_flash_t;

#define CONFIG_MAGIC 0x53415057U  /* "SAPW" */

static config_flash_t active_config;

static uint32_t crc32(const uint8_t *data, uint32_t len)
{
    uint32_t crc = 0xFFFFFFFFU;
    for (uint32_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int b = 0; b < 8; b++) {
            if (crc & 1) crc = (crc >> 1) ^ 0xEDB88320U;
            else         crc >>= 1;
        }
    }
    return ~crc;
}

int storage_init(void)
{
    uint8_t buf[sizeof(config_flash_t)];
    flash_read(FLASH_CONFIG_ADDR, buf, sizeof(buf));
    memcpy(&active_config, buf, sizeof(buf));

    /* Validate magic and CRC */
    uint32_t crc = crc32(buf, sizeof(config_flash_t) - 4);
    if (active_config.magic != CONFIG_MAGIC || active_config.crc != crc) {
        /* First boot or corrupted — load defaults */
        active_config.magic = CONFIG_MAGIC;
        active_config.measurement_interval_min = MEASUREMENT_INTERVAL_S / 60;
        active_config.sapwood_area_cm2 = SAPWOOD_AREA_DEFAULT_CM2;
        active_config.wound_factor = WOUND_FACTOR_DEFAULT;
        active_config.k_xylem = K_XYLEM_DEFAULT;
        active_config.zero_flow_offset = 0.0f;
        active_config.zero_cal_valid = 0;
        memset(active_config.dev_eui, 0, 8);
        memset(active_config.app_eui, 0, 8);
        memset(active_config.app_key, 0, 16);
        storage_save_config();
    }
    return 0;
}

int storage_save_config(void)
{
    active_config.crc = crc32((uint8_t *)&active_config,
                              sizeof(config_flash_t) - 4);
    flash_erase_sector(FLASH_CONFIG_ADDR);
    flash_write(FLASH_CONFIG_ADDR, (uint8_t *)&active_config,
                sizeof(config_flash_t));
    return 0;
}

int storage_get_credentials(uint8_t *deveui, uint8_t *appeui, uint8_t *appkey)
{
    if (active_config.dev_eui[0] == 0)
        return -1;  /* not provisioned */
    memcpy(deveui, active_config.dev_eui, 8);
    memcpy(appeui, active_config.app_eui, 8);
    memcpy(appkey, active_config.app_key, 16);
    return 0;
}

int storage_set_credentials(const uint8_t *deveui, const uint8_t *appeui,
                             const uint8_t *appkey)
{
    memcpy(active_config.dev_eui, deveui, 8);
    memcpy(active_config.app_eui, appeui, 8);
    memcpy(active_config.app_key, appkey, 16);
    return storage_save_config();
}

float storage_get_sapwood_area(void) { return active_config.sapwood_area_cm2; }
float storage_get_wound_factor(void) { return active_config.wound_factor; }
float storage_get_k_xylem(void) { return active_config.k_xylem; }
uint16_t storage_get_interval(void) { return active_config.measurement_interval_min; }

void storage_set_sapwood_area(float a) { active_config.sapwood_area_cm2 = a; storage_save_config(); }
void storage_set_wound_factor(float f) { active_config.wound_factor = f; storage_save_config(); }
void storage_set_interval(uint16_t min) { active_config.measurement_interval_min = min; storage_save_config(); }

/*
 * Measurement log ring buffer.
 * Each entry: 16 bytes
 *   [0-1] timestamp offset (minutes since boot, uint16)
 *   [2-3] sap_flux × 100 (int16)
 *   [4-5] sapwood_temp × 100 (int16)
 *   [6-7] air_temp × 100 (int16)
 *   [8-9] humidity × 100 (uint16)
 *   [10]  battery_pct (uint8)
 *   [11]  flags (uint8)
 *   [12-15] reserved
 */
static uint16_t log_write_idx = 0;

int storage_log_add(const log_entry_t *entry)
{
    uint8_t buf[LOG_ENTRY_BYTES];
    buf[0] = (entry->timestamp_min >> 8) & 0xFF;
    buf[1] = entry->timestamp_min & 0xFF;

    int16_t sf = (int16_t)(entry->sap_flux_cmh * 100.0f);
    buf[2] = (sf >> 8) & 0xFF;
    buf[3] = sf & 0xFF;

    int16_t st = (int16_t)(entry->sapwood_temp * 100.0f);
    buf[4] = (st >> 8) & 0xFF;
    buf[5] = st & 0xFF;

    int16_t at = (int16_t)(entry->air_temp * 100.0f);
    buf[6] = (at >> 8) & 0xFF;
    buf[7] = at & 0xFF;

    uint16_t rh = (uint16_t)(entry->humidity * 100.0f);
    buf[8] = (rh >> 8) & 0xFF;
    buf[9] = rh & 0xFF;

    buf[10] = entry->battery_pct;
    buf[11] = entry->flags;
    buf[12] = 0; buf[13] = 0; buf[14] = 0; buf[15] = 0;

    uint32_t addr = FLASH_LOG_ADDR + (uint32_t)log_write_idx * LOG_ENTRY_BYTES;
    /* For simplicity, write to flash (in production, batch-erase periodically) */
    flash_write(addr, buf, LOG_ENTRY_BYTES);

    log_write_idx = (log_write_idx + 1) % LOG_MAX_ENTRIES;
    return 0;
}

int storage_log_count(void)
{
    return (int)log_write_idx;
}