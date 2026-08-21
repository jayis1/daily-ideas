/*
 * Phase Scope — Calibration routines
 * Stores and retrieves calibration constants from STM32 flash option bytes
 */

#include "calibration.h"
#include "main.h"
#include <string.h>

/* ------------------------------------------------------------------ */
/* Flash storage for calibration data                                   */
/* Using last 2 pages of flash (bank 2, pages 127-128)                 */
/* Page size: 2KB, so we have 4KB for calibration data                  */
/* ------------------------------------------------------------------ */

#define CAL_FLASH_ADDR  0x0807F800  /* Last page of bank 2 */
#define CAL_MAGIC       0x50484353   /* "SCHP" — Phase Scope magic */

typedef struct {
    uint32_t magic;
    uint32_t version;
    calibration_t cal;
    uint32_t crc;
} cal_flash_t;

/* ------------------------------------------------------------------ */
/* CRC32 calculation                                                    */
/* ------------------------------------------------------------------ */

static uint32_t crc32(const uint8_t *data, uint32_t len)
{
    uint32_t crc = 0xFFFFFFFF;
    for (uint32_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1)
                crc = (crc >> 1) ^ 0xEDB88320;
            else
                crc >>= 1;
        }
    }
    return crc ^ 0xFFFFFFFF;
}

/* ------------------------------------------------------------------ */
/* Load calibration from flash                                         */
/* ------------------------------------------------------------------ */

int calibration_load(calibration_t *cal)
{
    const cal_flash_t *flash = (const cal_flash_t *)CAL_FLASH_ADDR;

    /* Check magic number */
    if (flash->magic != CAL_MAGIC) {
        /* No calibration stored — use defaults */
        return -1;
    }

    /* Verify CRC */
    uint32_t computed_crc = crc32((const uint8_t *)flash,
                                   sizeof(cal_flash_t) - sizeof(uint32_t));
    if (computed_crc != flash->crc) {
        /* CRC mismatch — use defaults */
        return -2;
    }

    /* Check version */
    if (flash->version != 1) {
        return -3;
    }

    /* Copy calibration data */
    memcpy(cal, &flash->cal, sizeof(calibration_t));
    return 0;
}

/* ------------------------------------------------------------------ */
/* Save calibration to flash                                            */
/* ------------------------------------------------------------------ */

int calibration_save(const calibration_t *cal)
{
    cal_flash_t buf;
    buf.magic = CAL_MAGIC;
    buf.version = 1;
    memcpy(&buf.cal, cal, sizeof(calibration_t));

    /* Compute CRC */
    buf.crc = crc32((const uint8_t *)&buf, sizeof(cal_flash_t) - sizeof(uint32_t));

    /* Unlock flash */
    FLASH->KEYR = 0x45670123;
    FLASH->KEYR = 0xCDEF89AB;

    /* Wait for flash ready */
    while (FLASH->SR & FLASH_SR_BSY)
        ;

    /* Erase last page */
    FLASH->CR |= FLASH_CR_PER;
    FLASH->CR = (FLASH->CR & ~FLASH_CR_PNB) | ((127 << FLASH_CR_PNB_Pos) & FLASH_CR_PNB);
    FLASH->CR |= FLASH_CR_STRT;

    while (FLASH->SR & FLASH_SR_BSY)
        ;

    /* Clear PER bit */
    FLASH->CR &= ~FLASH_CR_PER;

    /* Check for errors */
    if (FLASH->SR & FLASH_SR_PGAERR) return -4;
    if (FLASH->SR & FLASH_SR_WRPERR) return -5;

    /* Program data (8 bytes at a time for STM32G4) */
    FLASH->CR |= FLASH_CR_PG;

    uint64_t *dst = (uint64_t *)CAL_FLASH_ADDR;
    uint64_t *src = (uint64_t *)&buf;

    for (uint32_t i = 0; i < sizeof(cal_flash_t) / 8; i++) {
        dst[i] = src[i];
        while (FLASH->SR & FLASH_SR_BSY)
            ;
    }

    FLASH->CR &= ~FLASH_CR_PG;

    /* Lock flash */
    FLASH->CR |= FLASH_CR_LOCK;

    return 0;
}

/* ------------------------------------------------------------------ */
/* Run self-calibration                                                 */
/* ------------------------------------------------------------------ */

int calibration_run(calibration_t *cal, const float *v_known, const float *i_known)
{
    /* This function should be called when known reference signals
     * are applied. v_known[3] and i_known[3] contain the known
     * RMS values for each channel.
     *
     * The function reads the current ADC values and computes
     * gain factors to match the known values.
     */

    /* In a real implementation, this would:
     * 1. Read current ADC values for each channel
     * 2. Compute raw RMS from ADC
     * 3. Calculate gain = known_value / raw_value
     * 4. Calculate offset (with zero input)
     * 5. Store to flash
     *
     * For now, this is a placeholder.
     */

    (void)v_known;
    (void)i_known;

    return 0;
}