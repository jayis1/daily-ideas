/*
 * gossamer-spin / firmware / sd_log.c
 * FatFs microSD process logging at 10 Hz.
 *
 * CSV format:
 *   time_s,voltage_kv,flow_mlh,drum_rpm,jet_current_na,jet_sigma_na,
 *   jet_state,temp_c,rh_pct
 */
#include "main.h"

static struct {
    bool  open;
    int   samples;
} log = { false, 0 };

static void *h_spi2 = (void *)1;
static void *h_fatfs = (void *)1;

static const char *JET_STATE_CSV[5] = {
    "idle", "stable", "interrupted", "unstable", "dripping"
};

void sd_log_init(void)
{
    /* In real build:
       - f_mount(&fatfs, "", 1)
       - f_open(&file, "spin_log.csv", FA_WRITE | FA_CREATE_ALWAYS)
       - f_write header line:
         "time_s,voltage_kv,flow_mlh,drum_rpm,jet_current_na,"
         "jet_sigma_na,jet_state,temp_c,rh_pct\n" */
    (void)h_spi2;
    (void)h_fatfs;
    log.open = true;
    log.samples = 0;
}

void sd_log_write(process_t *p)
{
    if (!log.open) return;

    /* In real build:
       - Format CSV line
       - f_write(&file, line, strlen(line), &bw)
       - f_sync(&file) every 10 samples (1/sec) to reduce wear */
    char line[128];
    const char *js = JET_STATE_CSV[p->jet_state < 5 ? p->jet_state : 0];
    snprintf(line, sizeof(line),
             "%lu,%.2f,%.3f,%.1f,%.1f,%.1f,%s,%.2f,%.2f\n",
             (unsigned long)p->elapsed_s,
             p->voltage_kv, p->flow_mlh, p->drum_rpm,
             p->current_na, p->jet_sigma_na, js,
             p->temp_c, p->rh_pct);
    (void)line;  /* would be written to file */

    log.samples++;
}

void sd_log_close(void)
{
    if (!log.open) return;

    /* In real build: f_close(&file) */
    log.open = false;
}