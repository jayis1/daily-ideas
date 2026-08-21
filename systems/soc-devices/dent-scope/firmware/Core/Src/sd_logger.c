/*
 * dent-scope / Core/Src/sd_logger.c
 * Dent Scope — SD card FATFS CSV + binary logging
 * MIT License.
 */
#include "sd_logger.h"
#include "ff.h"
#include "diskio.h"

static FATFS fs;
static FIL log_file;
static int run_counter = 0;
static bool sd_ok = false;

void sd_init(void)
{
    if (f_mount(&fs, "0:", 1) == FR_OK) {
        sd_ok = true;
    }
}

void sd_open_run(uint32_t run_id)
{
    if (!sd_ok) return;
    char fname[32];
    run_counter++;
    snprintf(fname, sizeof(fname), "0:/indent_%04d.csv", run_counter);
    if (f_open(&log_file, fname, FA_CREATE_ALWAYS | FA_WRITE) == FR_OK) {
        /* CSV header */
        f_puts("t_ms,force_mN,depth_um,state\n", &log_file);
    }
}

void sd_log_point(float force_mN, float depth_um, int state, uint32_t t_ms)
{
    if (!sd_ok) return;
    char line[80];
    int n = snprintf(line, sizeof(line), "%lu,%.1f,%.3f,%d\n",
                     (unsigned long)t_ms, force_mN, depth_um, state);
    f_write(&log_file, line, n, NULL);
    f_sync(&log_file);
}

void sd_close_run(void)
{
    if (!sd_ok) return;
    f_close(&log_file);
}