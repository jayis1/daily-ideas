/*
 * sdlog.c — FatFS CSV + binary waveform logging
 *
 * Every sferic is logged as a row in /sd/SFERIC_YYYYMMDD.csv:
 *
 *   ts_iso,type,conf,bearing,distance_km,peak_uv,rise_us,slow_tail,flash_rate
 *
 * and the 50 ms x 3-channel waveform is written to
 * /sd/WAVE/<timestamp>.bin  (3 x 400 x int16 = 2400 bytes, gzip-friendly).
 *
 * The CSV is opened in append mode and flushed every 10 s (or on the LOG
 * button) to survive power loss — the same durability strategy as
 * Hive Mind (#7) and Tremor Tile (#6).
 */
#include "sdlog.h"
#include "esp_log.h"
#include "esp_vfs_fat.h"
#include "driver/sdspi_host.h"
#include "driver/sdmmc_host.h"
#include "ff.h"
#include <stdio.h>
#include <string.h>

static const char *TAG = "sdlog";
static FATFS s_fs;
static FILE *s_csv;
static char  s_csv_name[40];

int sdlog_mount(void)
{
    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    sdspi_device_config_t dev = {
        .gpio_cs = 13,
        .host_id = SDSPI_DEFAULT_HOST,
    };
    esp_vfs_fat_sdmmc_mount_config_t cfg = {
        .format_if_mount_failed = false,
        .max_files = 5,
        .allocation_unit_size = 16 * 1024,
    };
    esp_err_t err = esp_vfs_fat_sdspi_mount("/sd", &host, &dev, &cfg, &s_fs);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "SD mount failed: %s", esp_err_to_name(err));
        return -1;
    }
    ESP_LOGI(TAG, "SD mounted on /sd");
    return 0;
}

static void open_csv_for_today(const stroke_t *st)
{
    /* Derive YYYYMMDD from the GPS timestamp (simplified: use ESP32 RTC). */
    time_t now = (time_t)(st->ts_us / 1000000ULL);
    struct tm tm; gmtime_r(&now, &tm);
    snprintf(s_csv_name, sizeof(s_csv_name),
             "/sd/SFERIC_%04d%02d%02d.csv",
             tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday);
    s_csv = fopen(s_csv_name, "a");
    if (s_csv) {
        fputs("iso_ts,type,conf,bearing,distance_km,peak_uv,"
              "rise_us,slow_tail,flash_rate\n", s_csv);
    }
}

void sdlog_sferic(const stroke_t *st)
{
    if (!s_csv) open_csv_for_today(st);
    if (!s_csv) return;

    const char *tn[] = { "CG", "IC", "CC" };
    time_t now = (time_t)(st->ts_us / 1000000ULL);
    struct tm tm; gmtime_r(&now, &tm);
    char iso[24];
    strftime(iso, sizeof(iso), "%Y-%m-%dT%H:%M:%SZ", &tm);

    fprintf(s_csv, "%s,%s,%.2f,%.1f,%.1f,%.1f,%.1f,%.3f,%.1f\n",
            iso,
            tn[st->cls.label],
            st->cls.conf,
            st->geo.azimuth_deg,
            st->geo.distance_km,
            st->geo.peak_field_uv,
            st->sf.rise_us,
            st->sf.slow_tail_ratio,
            0.0f);
    fflush(s_csv);

    /* Write the waveform blob. */
    char wname[60];
    snprintf(wname, sizeof(wname), "/sd/WAVE/%llu.bin",
             (unsigned long long)st->ts_us);
    FILE *wf = fopen(wname, "wb");
    if (wf) {
        fwrite(st->sf.wave_ns, sizeof(int16_t), SFERIC_WIN, wf);
        fwrite(st->sf.wave_ew, sizeof(int16_t), SFERIC_WIN, wf);
        fwrite(st->sf.wave_e,  sizeof(int16_t), SFERIC_WIN, wf);
        fclose(wf);
    }
}

void sdlog_flush(void)
{
    if (s_csv) fflush(s_csv);
}