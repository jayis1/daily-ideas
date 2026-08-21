/*
 * sonar-cast / firmware / sd_log.c
 * FatFs bathymetry CSV + binary raw-echo logging to microSD.
 */
#include "main.h"
#include <stdio.h>

static bool sd_ok = false;
static char fname_csv[32];
static char fname_bin[32];

void sd_log_init(void)
{
    /* FatFs f_mount(SD, ...) — placeholder. */
    sd_ok = true;
    snprintf(fname_csv, sizeof(fname_csv), "bathy_%lu.csv",
             (unsigned long)millis() / 1000);
    snprintf(fname_bin, sizeof(fname_bin), "echo_%lu.bin",
             (unsigned long)millis() / 1000);

    if (sd_ok) {
        /* Write CSV header */
        const char *hdr = "unix_ts,lat,lon,hdop,depth_m,bottom_type,"
                          "fish_count,fish_avg_cm,temp_c,sound_speed,tilt_deg\n";
        /* f_open(&file, fname_csv, FA_CREATE_ALWAYS | FA_WRITE); f_puts(hdr) */
        (void)hdr;
    }
}

void sd_log_write(const sonar_result_t *r)
{
    if (!sd_ok) return;

    /* Average fish length for compactness */
    float avg_len = 0;
    if (r->fish_count > 0) {
        for (uint8_t i = 0; i < r->fish_count; i++)
            avg_len += r->fish_lengths[i];
        avg_len /= r->fish_count;
    }

    char line[192];
    int n = snprintf(line, sizeof(line),
        "%lu,%.6f,%.6f,%.1f,%.2f,%s,%u,%.1f,%.2f,%.1f,%.1f\n",
        (unsigned long)r->unix_ts,
        r->lat, r->lon, r->hdop,
        r->depth_m, BOTTOM_NAMES[r->bottom_type],
        r->fish_count, avg_len,
        r->temp_c, r->sound_speed, r->tilt_deg);
    (void)n;
    /* f_puts(line, &file) — flush every 16 pings to reduce wear */
}