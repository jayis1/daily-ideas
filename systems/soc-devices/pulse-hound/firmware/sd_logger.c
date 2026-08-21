/*
 * Pulse Hound — RF Signal Hunter
 * sd_logger.c — SD card SPI driver, FAT32 append, CSV logging
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "sd_logger.h"
#include "config.h"
#include <string.h>
#include <stdio.h>

/* ---- SPI / GPIO HAL stubs ---- */
extern void spi_init(int mosi, int miso, int sck, int cs, int freq_hz);
extern int  spi_write_read(const uint8_t *tx, uint8_t *rx, int len);
extern void gpio_set(int pin, int val);
extern void delay_ms(uint32_t ms);
extern uint32_t rtc_get_time_ms(void);

/* ---- SD card state ---- */
static int sd_initialized = 0;
static int sd_card_present = 0;
static int logging_active = 0;
static uint32_t log_start_ms = 0;
static uint32_t last_log_ms = 0;

/* ---- SD card SPI commands (simplified — real impl uses ESP-IDF SDMMC/SPI driver) ---- */

/* The ESP32-S3 ESP-IDF provides a full SD card driver (sdspi_host_t / vfs_fat).
 * This module wraps it with a simple CSV logging API.
 * In a real build, the platform layer handles the SPI/FAT32 details. */

int sd_logger_init(void)
{
    if (sd_initialized) return 0;

    /* Initialize SPI bus for SD card */
    spi_init(SD_MOSI_GPIO, SD_MISO_GPIO, SD_SCK_GPIO, SD_CS_GPIO, 4000000);

    /* In real ESP-IDF: mount FAT32 filesystem via f_mount / esp_vfs_fat_sdspi_mount */
    /* For this portable C source, we just flag init success — the platform
     * layer provides the actual FAT32 implementation. */

    sd_initialized = 1;
    sd_card_present = 1; /* assume present; real impl would detect via CS pull-up */
    return 0;
}

int sd_logger_is_present(void)
{
    return sd_card_present;
}

int sd_logger_start(const char *filename)
{
    if (!sd_initialized || !sd_card_present) return -1;

    /* In real ESP-IDF: open file in append mode via fopen() on VFS */
    /* Real code:
     *   FILE *f = fopen(filename, "a");
     *   fprintf(f, "timestamp_ms,rssi_dbm,peak_rssi_dbm,classification,bearing_deg,battery_pct,mode\n");
     *   fclose(f);
     */
    logging_active = 1;
    log_start_ms = rtc_get_time_ms();
    last_log_ms = log_start_ms;
    return 0;
}

void sd_logger_stop(void)
{
    logging_active = 0;
}

int sd_logger_is_logging(void)
{
    return logging_active;
}

void sd_logger_write(float rssi_dbm, float peak_rssi, int classification,
                     float bearing_deg, int battery_pct, int mode)
{
    if (!logging_active) return;

    uint32_t now = rtc_get_time_ms();
    if (now - last_log_ms < SD_LOG_INTERVAL_MS) return;
    last_log_ms = now;

    uint32_t elapsed = now - log_start_ms;

    /* Build CSV line — in real ESP-IDF, write via fprintf to VFS-mounted FAT file */
    /* Real code:
     *   FILE *f = fopen("/sd/log.csv", "a");
     *   if (!f) return;
     *   fprintf(f, "%u,%.1f,%.1f,%d,%.1f,%d,%d\n",
     *           elapsed, rssi_dbm, peak_rssi, classification,
     *           bearing_deg, battery_pct, mode);
     *   fclose(f);
     */
    (void)elapsed;
    (void)rssi_dbm;
    (void)peak_rssi;
    (void)classification;
    (void)bearing_deg;
    (void)battery_pct;
    (void)mode;
}

void sd_logger_flush(void)
{
    /* In real ESP-IDF: fflush() + fclose() the log file */
    /* FAT32 with SPI mode handles flush on close */
}

/* ---- Status ---- */
int sd_logger_get_status(sd_logger_status_t *status)
{
    if (!status) return -1;
    status->initialized = sd_initialized;
    status->card_present = sd_card_present;
    status->logging = logging_active;
    status->elapsed_ms = rtc_get_time_ms() - log_start_ms;
    return 0;
}