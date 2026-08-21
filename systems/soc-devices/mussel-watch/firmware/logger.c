/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * logger.c — SD card FAT32 logging
 *
 * Logs telemetry to a micro-SD card in CSV format, one file per day.
 * Each row: timestamp,mussel_a,mussel_b,mussel_c,mussel_d,temp_c,do_mgl,depth_m,battery_v,alert
 *
 * The SD card uses SPI mode (MOSI, MISO, SCK, CS shared with SX1262 via
 * separate CS lines). The nRF SDK provides FATFS via the sd_spi driver.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "logger.h"
#include "config.h"
#include <string.h>
#include <stdio.h>

/* ---- Platform HAL stubs ---- */
extern void spi_init(int mosi, int miso, int sck, int cs, int freq_hz);
extern void gpio_set(int pin, int val);
extern void delay_ms(uint32_t ms);

/* nRF SDK FATFS wrappers (port layer provides these) */
extern int  fatfs_mount(void);
extern int  fatfs_open(const char *path, int append);
extern int  fatfs_write(const char *data, int len);
extern int  fatfs_close(void);
extern int  fatfs_sync(void);

static int logger_mounted = 0;
static char current_filename[32] = {0};

int logger_init(void)
{
    /* Power on the SD card via load switch */
    gpio_set(PIN_SD_PWR, 1);
    delay_ms(250);  /* SD card power-up stabilization */

    /* Initialize SPI for SD card (shared bus, SD CS active) */
    /* In the nRF SDK, the sd_spi driver handles bus arbitration with SX1262
     * by asserting/deasserting CS lines. */
    spi_init(PIN_SPI_MOSI, PIN_SPI_MISO, PIN_SPI_SCK, PIN_SD_CS, 400000);  /* 400 kHz init */

    if (fatfs_mount() < 0)
        return -1;

    logger_mounted = 1;
    return 0;
}

int logger_mount(void)
{
    if (logger_mounted)
        return 0;
    return logger_init();
}

int logger_unmount(void)
{
    if (!logger_mounted)
        return 0;
    fatfs_sync();
    fatfs_close();
    gpio_set(PIN_SD_PWR, 0);
    logger_mounted = 0;
    return 0;
}

void logger_get_filename(char *buf, int len, uint32_t timestamp_s)
{
    /* Convert Unix timestamp to YYYY-MM-DD for filename.
     * This is a simplified calculation; the nRF SDK provides a full RTC
     * calendar, but we implement a portable version here. */
    /* Days since epoch */
    uint32_t days = timestamp_s / 86400;
    /* Simple Gregorian conversion (valid 1970–2099) */
    int year = 1970;
    int month = 1;
    int day = 1;

    /* Approximate year */
    while (1) {
        int days_in_year = ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0) ? 366 : 365;
        if (days < (uint32_t)days_in_year) break;
        days -= days_in_year;
        year++;
    }

    /* Approximate month */
    int days_in_month[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0)
        days_in_month[1] = 29;  /* leap year February */

    while (days >= (uint32_t)days_in_month[month - 1]) {
        days -= days_in_month[month - 1];
        month++;
    }
    day = (int)days + 1;

    snprintf(buf, len, "/%04d-%02d-%02d.csv", year, month, day);
}

int logger_log(const mussel_watch_state_t *st, uint32_t timestamp_s)
{
    if (!logger_mounted)
        if (logger_mount() < 0)
            return -1;

    /* Determine the log filename for today */
    char fname[32];
    logger_get_filename(fname, sizeof(fname), timestamp_s);

    /* If the filename changed (new day), close the old file and open new */
    if (strcmp(fname, current_filename) != 0) {
        fatfs_close();
        strcpy(current_filename, fname);
        /* Open in append mode; if the file doesn't exist, create it and write header */
        if (fatfs_open(fname, 1) < 0)
            return -1;
    }

    /* Build the CSV line */
    char line[256];
    int pos = 0;
    pos += snprintf(&line[pos], sizeof(line) - pos, "%lu", (unsigned long)timestamp_s);

    /* Gape angles for all 4 mussels (or 'NaN' if invalid) */
    for (int i = 0; i < MAX_MUSSELS; i++) {
        if (i < st->n_mussels && st->gape_angle[i] >= 0) {
            pos += snprintf(&line[pos], sizeof(line) - pos, ",%.2f", st->gape_angle[i]);
        } else {
            pos += snprintf(&line[pos], sizeof(line) - pos, ",NaN");
        }
    }

    /* Water quality + battery + alert */
    pos += snprintf(&line[pos], sizeof(line) - pos,
                    ",%.2f,%.2f,%.2f,%.2f,%d",
                    st->water_temp_c,
                    st->dissolved_o2_mgl,
                    st->water_depth_m,
                    st->battery_v,
                    (int)st->current_alert);

    pos += snprintf(&line[pos], sizeof(line) - pos, "\r\n");

    fatfs_write(line, pos);
    fatfs_sync();

    return 0;
}

int logger_log_calibration(const mussel_watch_state_t *st, int channel, const char *event)
{
    if (!logger_mounted)
        if (logger_mount() < 0)
            return -1;

    char line[128];
    int pos = snprintf(line, sizeof(line),
                       "# CAL ch%d %s closed_mv=%.1f open_mv=%.1f\r\n",
                       channel, event,
                       st->cal_closed_mv[channel],
                       st->cal_open_mv[channel]);
    fatfs_write(line, pos);
    fatfs_sync();
    return 0;
}

int logger_log_alert(const mussel_watch_state_t *st, alert_code_t code, uint32_t timestamp_s)
{
    if (!logger_mounted)
        if (logger_mount() < 0)
            return -1;

    extern const char *anomaly_alert_name(alert_code_t code);
    char line[128];
    int pos = snprintf(line, sizeof(line),
                       "# ALERT %lu code=%d (%s) battery=%.2f%%\r\n",
                       (unsigned long)timestamp_s,
                       (int)code,
                       anomaly_alert_name(code),
                       (double)st->battery_pct);
    fatfs_write(line, pos);
    fatfs_sync();
    return 0;
}