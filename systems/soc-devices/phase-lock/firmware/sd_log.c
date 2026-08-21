/*
 * sd_log.c — microSD card FAT32 CSV logging via SPI1
 *
 * Uses a minimal SPI + SD card driver (raw block reads/writes).
 * Writes CSV files to a FAT32 partition. The implementation below
 * is a simplified placeholder that uses the STM32 HAL SD driver
 * if available; in a real build, link a PetitFS or FatFS layer.
 *
 * File formats:
 *   SWP_NNNN.csv — header: f, a, R, theta, X, Y, noise, ts_ms
 *   TRC_NNNN.csv — header: ts_ms, R, theta, X, Y, noise
 */

#include "stm32g491_conf.h"
#include "sd_log.h"
#include "spi.h"
#include <string.h>
#include <stdio.h>

static bool sd_ok = false;
static uint16_t cur_run = 0;
static bool sweep_open = false;
static bool trace_open  = false;

void sd_log_init(void)
{
    spi_init();
    sd_ok = sd_card_init();
}

bool sd_log_ready(void) { return sd_ok; }

void sd_log_open_sweep(uint16_t run_id)
{
    cur_run = run_id;
    char hdr[64];
    snprintf(hdr, sizeof(hdr),
        "# SWP_%04u.csv — Phase Lock sweep log\r\n"
        "f,a,R,theta,X,Y,noise,ts_ms\r\n", run_id);
    /* Open file on SD and write header (FatFS call) */
    sd_file_write_start("SWP", run_id, hdr);
    sweep_open = true;
}

void sd_log_sweep_point(const sweep_point_t *p)
{
    if (!sweep_open) return;
    char line[96];
    snprintf(line, sizeof(line), "%.3f,%.4f,%.6f,%.4f,%.6f,%.6f,%.3e,%lu\r\n",
             p->f, p->a, p->R, p->theta, p->X, p->Y, p->noise, (unsigned long)p->ts_ms);
    sd_file_append(line);
}

void sd_log_close(void)
{
    if (sweep_open || trace_open) {
        sd_file_write_end();
        sweep_open = false;
        trace_open = false;
    }
}

void sd_log_open_trace(uint16_t run_id, float freq, float tc_label)
{
    cur_run = run_id;
    char hdr[96];
    snprintf(hdr, sizeof(hdr),
        "# TRC_%04u.csv — Phase Lock time-trace\r\n"
        "# f=%.3f Hz, TC=%.3f s\r\n"
        "ts_ms,R,theta,X,Y,noise\r\n", run_id, freq, tc_label);
    sd_file_write_start("TRC", run_id, hdr);
    trace_open = true;
}

void sd_log_trace_row(uint32_t ts_ms, float R, float theta, float X, float Y, float noise)
{
    if (!trace_open) return;
    char line[96];
    snprintf(line, sizeof(line), "%lu,%.6f,%.4f,%.6f,%.6f,%.3e\r\n",
             (unsigned long)ts_ms, R, theta, X, Y, noise);
    sd_file_append(line);
}