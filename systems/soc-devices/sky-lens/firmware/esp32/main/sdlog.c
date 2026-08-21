/*
 * sdlog.c — FatFS event CSV + daily JSON rollup
 *
 * Every coincidence event is appended to /EVENTS/ev_YYYYMMDD.csv.
 * At local midnight a daily_YYYYMMDD.json rollup is written with the
 * corrected flux, zenith histogram, skymap, and lifetime fit.
 */
#include "sdlog.h"
#include "sky_lens.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "esp_vfs_fat.h"
#include "esp_log.h"
#include "driver/sdmmc_host.h"
#include "driver/sdspi_host.h"
static const char *TAG = "sdlog";
static sdmmc_card_t *s_card;
static bool s_mounted = false;
#endif

void sdlog_init(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("sdlog init (sim)");
#else
    /* Mount the SD card on /sdcard via SDSPI (GPIO11-14) */
    sdmmc_host_t host = SDSPI_HOST_DEFAULT();
    sdspi_slot_config_t slot = SDSPI_SLOT_CONFIG_DEFAULT();
    slot.gpio_cs = 14;
    sdspi_host_init();
    sdspi_host_init_slot(host.slot, &slot);
    esp_vfs_fat_sdmmc_mount_config_t mcfg = {
        .format_if_mount_failed = false,
        .max_files = 5,
        .allocation_unit_size = 512
    };
    esp_err_t ret = esp_vfs_fat_sdmmc_mount("/sdcard", &host, &slot, &mcfg, &s_card);
    if (ret == ESP_OK) {
        s_mounted = true;
        ESP_LOGI(TAG, "SD mounted");
    } else {
        ESP_LOGW(TAG, "SD mount failed: %s", esp_err_to_name(ret));
    }
#endif
}

static void date_str(uint64_t ts_us, char *buf, int len)
{
    /* Simplified: use the simulator or RTC time */
#ifdef SKY_LENS_SIM
    port_sim_date(buf, len);
#else
    time_t t = (time_t)(ts_us / 1000000ULL);
    struct tm tm;
    gmtime_r(&t, &tm);
    strftime(buf, len, "%Y%m%d", &tm);
#endif
}

void sdlog_write_event(const event_t *ev)
{
    char datebuf[16];
    date_str(ev->ts_us, datebuf, sizeof(datebuf));
    char path[64];
    snprintf(path, sizeof(path),
#ifdef SKY_LENS_SIM
             "EVENTS/ev_%s.csv", datebuf);
#else
             "/sdcard/EVENTS/ev_%s.csv", datebuf);
#endif

#ifdef SKY_LENS_SIM
    /* Sim: record to the simulator's in-memory log */
    port_sim_log("event seq=%lu h0=%d h1=%d dt=%ldps zen=%.1f az=%.1f P=%.1f",
                 (unsigned long)ev->seq, ev->h0_mv, ev->h1_mv,
                 (long)ev->dt_ps, ev->zenith_deg, ev->az_deg, ev->p_hpa);
#else
    if (!s_mounted) return;
    FILE *f = fopen(path, "a");
    if (!f) return;
    fprintf(f, "%llu,%lu,%d,%d,%ld,%.2f,%.2f,%.4f,%.4f,%.4f,%.4f,%.2f,%.2f,%u\n",
            (unsigned long long)ev->ts_us, (unsigned long)ev->seq,
            ev->h0_mv, ev->h1_mv, (long)ev->dt_ps,
            ev->zenith_deg, ev->az_deg,
            ev->q_w, ev->q_x, ev->q_y, ev->q_z, ev->p_hpa, ev->t_c, ev->flags);
    fclose(f);
#endif
}

void sdlog_write_daily(const skymap_t *m, const zenith_fit_t *z,
                       const daily_t *d, const lifetime_result_t *lf)
{
    char datebuf[16];
    date_str(d->end_us, datebuf, sizeof(datebuf));
    char path[64];
    snprintf(path, sizeof(path),
#ifdef SKY_LENS_SIM
             "EVENTS/daily_%s.json", datebuf);
#else
             "/sdcard/EVENTS/daily_%s.json", datebuf);
#endif

#ifdef SKY_LENS_SIM
    port_sim_log("daily rollup: events=%lu rate=%.1f corr=%.1f I0=%.1f tau=%.3f",
                 (unsigned long)d->n_events, d->rate_raw_cpm,
                 d->rate_corr_cpm, z->i0, lf->tau_us);
#else
    if (!s_mounted) return;
    FILE *f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "{\"date\":\"%s\",\"events\":%lu,\"rate_raw_cpm\":%.3f,"
               "\"rate_corr_cpm\":%.3f,\"mean_p_hpa\":%.2f,\"mean_t_c\":%.2f,"
               "\"zenith_i0\":%.3f,\"zenith_chi2\":%.3f,"
               "\"skymap_total\":%lu,"
               "\"lifetime_tau_us\":%.4f,\"lifetime_err_us\":%.4f,"
               "\"lifetime_pairs\":%lu}\n",
            datebuf, (unsigned long)d->n_events,
            d->rate_raw_cpm, d->rate_corr_cpm, d->mean_p_hpa, d->mean_t_c,
            z->i0, z->chi2, (unsigned long)m->total,
            lf->tau_us, lf->tau_err_us, (unsigned long)lf->n_pairs);
    fclose(f);
    ESP_LOGI(TAG, "daily rollup written: %s", path);
#endif
}