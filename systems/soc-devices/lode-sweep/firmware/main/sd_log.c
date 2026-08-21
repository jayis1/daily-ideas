/*
 * lode-sweep / firmware / sd_log.c
 * FatFs survey CSV logging to microSD.
 *
 * Logs significant detections (signal above threshold) as CSV rows for
 * GPS-tagged survey mapping.
 */
#include "main.h"
#include <stdio.h>

static bool sd_ok = false;
static char fname_csv[32];

void sd_log_init(void)
{
    /* FatFs f_mount(SD, ...) — placeholder. */
    sd_ok = true;
    snprintf(fname_csv, sizeof(fname_csv), "survey_%lu.csv",
             (unsigned long)millis() / 1000);

    if (sd_ok) {
        /* Write CSV header */
        const char *hdr = "unix_ts,lat,lon,hdop,target_class,depth_cm,"
                          "confidence,signal,tilt_deg\n";
        /* f_open(&file, fname_csv, FA_CREATE_ALWAYS | FA_WRITE); f_puts(hdr) */
        (void)hdr;
    }
}

void sd_log_write(const sweep_result_t *r)
{
    if (!sd_ok) return;
    if (r->signal_strength < 0.05f) return;

    char line[192];
    int n = snprintf(line, sizeof(line),
        "%lu,%.6f,%.6f,%.1f,%s,%.1f,%.2f,%.4f,%.1f\n",
        (unsigned long)r->unix_ts,
        r->lat, r->lon, r->hdop,
        CLASS_NAMES[r->target_class],
        r->depth_cm, r->confidence,
        r->signal_strength, r->tilt_deg);
    (void)n;
    /* f_puts(line, &file) — flush every 16 detections to reduce wear */
}