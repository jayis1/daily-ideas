/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * sd_log.c — FatFs-based measurement & A-scan logging to MicroSD
 *
 * Uses SPI-mode SD card access (shared SPI1 with OLED, mutex-protected).
 * Measurements append to PINGLOG.CSV; A-scan raw captures are saved as
 * ASCAN_nnnn.BIN for later retrieval.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "sd_log.h"
#include "power.h"
#include <string.h>
#include <stdio.h>

/* FatFs (assumed available in the build) */
#include "ff.h"
#include "diskio.h"

static FATFS g_fs;
static uint8_t g_sd_ok = 0;
static uint32_t g_seq = 0;
static char g_line[128];

void sd_init(void)
{
    /* Enable GPIOB + SPI1 (shared with OLED, already configured in display_init).
     * SD CS = PB5. */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;

    /* PB5 (SD CS) → output, default high (deselected) */
    GPIOB->MODER = (GPIOB->MODER & ~GPIO_MODER_MODE5) |
                   (1U << GPIO_MODER_MODE5_Pos);
    GPIOB->OTYPER &= ~GPIO_OTYPER_OT5;
    GPIOB->BSRR = (1U << 5);   /* CS high */

    /* SD power gate (PC8) → output, high (on) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOCEN;
    GPIOC->MODER = (GPIOC->MODER & ~GPIO_MODER_MODE8) |
                   (1U << GPIO_MODER_MODE8_Pos);
    GPIOC->BSRR = (1U << 8);   /* SD power on */

    /* Wait for card power-up */
    for (volatile int i = 0; i < 100000; i++) { __NOP(); }

    /* Mount */
    FRESULT fr = f_mount(&g_fs, "0:", 1);
    g_sd_ok = (fr == FR_OK);
    g_seq = 0;
}

uint8_t sd_present(void)
{
    /* Detect via card-present switch (optional) or by mount status */
    return g_sd_ok;
}

uint8_t sd_log_measurement(const log_entry_t *entry)
{
    if (!g_sd_ok || !entry) return 0;

    /* Build CSV line: seq, timestamp, material, mode, thickness_mm,
     * tof_ns, velocity, gain, flaw, flaw_depth, flaw_equiv, battery */
    int n = snprintf(g_line, sizeof(g_line),
                     "%lu,%lu,%s,%u,%.3f,%.1f,%lu,%.1f,%u,%.2f,%.2f,%d\n",
                     entry->sequence,
                     entry->timestamp,
                     entry->material,
                     entry->mode,
                     entry->thickness_mm,
                     entry->tof_ns,
                     (unsigned long)entry->velocity_mps,
                     entry->gain_db,
                     entry->flaw_detected,
                     entry->flaw_depth_mm,
                     entry->flaw_equiv_mm,
                     entry->battery_pct);

    FIL f;
    FRESULT fr = f_open(&f, "PINGLOG.CSV", FA_OPEN_APPEND | FA_WRITE);
    if (fr != FR_OK) return 0;

    UINT written;
    fr = f_write(&f, g_line, (UINT)n, &written);
    f_close(&f);
    return (fr == FR_OK && (int)written == n) ? 1 : 0;
}

uint8_t sd_log_ascan(const ascan_t *scan, uint32_t seq)
{
    if (!g_sd_ok || !scan) return 0;

    char fname[16];
    snprintf(fname, sizeof(fname), "ASCAN_%04lu.BIN", seq);

    FIL f;
    FRESULT fr = f_open(&f, fname, FA_CREATE_ALWAYS | FA_WRITE);
    if (fr != FR_OK) return 0;

    UINT written;
    /* Header: count (2 bytes) + window_us (2) + valid (1) */
    uint8_t hdr[8] = {0};
    hdr[0] = (uint8_t)(scan->count & 0xFF);
    hdr[1] = (uint8_t)(scan->count >> 8);
    f_write(&f, hdr, 4, &written);
    /* Envelope samples (little-endian 16-bit) */
    f_write(&f, scan->envelope, scan->count * 2, &written);
    /* RF samples (if present) */
    if (scan->rf[0] != 0 || scan->rf[scan->count - 1] != 0)
        f_write(&f, scan->rf, scan->count * 2, &written);

    f_close(&f);
    g_seq = seq + 1;
    return 1;
}

uint8_t sd_log_read_recent(log_entry_t *out, uint8_t max_count)
{
    if (!g_sd_ok || !out) return 0;
    /* Simplified: read the last max_count lines of PINGLOG.CSV.
     * A full implementation would parse CSV. */
    FIL f;
    FRESULT fr = f_open(&f, "PINGLOG.CSV", FA_READ);
    if (fr != FR_OK) return 0;

    /* Seek to end to get size */
    FSIZE_t size = f_size(&f);
    FSIZE_t start = size > 4096 ? size - 4096 : 0;
    f_lseek(&f, start);

    /* Read and parse last lines (simplified — count only) */
    char buf[4096];
    UINT rd;
    f_read(&f, buf, sizeof(buf), &rd);
    f_close(&f);

    /* Count newlines */
    uint8_t count = 0;
    for (UINT i = 0; i < rd; i++)
        if (buf[i] == '\n') count++;
    if (count > max_count) count = max_count;
    return count;
}

uint32_t sd_log_count(void)
{
    if (!g_sd_ok) return 0;
    FIL f;
    FRESULT fr = f_open(&f, "PINGLOG.CSV", FA_READ);
    if (fr != FR_OK) return 0;
    /* Count lines */
    uint32_t lines = 0;
    char buf[512];
    UINT rd;
    do {
        fr = f_read(&f, buf, sizeof(buf), &rd);
        for (UINT i = 0; i < rd; i++)
            if (buf[i] == '\n') lines++;
    } while (rd > 0 && fr == FR_OK);
    f_close(&f);
    return lines;
}

void sd_sync(void)
{
    if (!g_sd_ok) return;
    f_sync(NULL);
    /* Unmount */
    f_mount(NULL, "0:", 0);
    g_sd_ok = 0;
    /* Power off SD */
    GPIOC->BSRR = (1U << (16 + 8));   /* PC8 low */
}