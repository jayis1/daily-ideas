/*
 * sd_log.c — SD card CSV + binary session logging
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * SPI3 SD card. Per-session CSV header + one row per spectrum (timestamp,
 * num_peaks, K0 list, compound, class, confidence, pressure, temps).
 *
 * SPDX-License-Identifier: MIT
 */
#include "sd_log.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"
#include <stdio.h>
#include <string.h>

extern SPI_HandleTypeDef hspi3;

static bool g_ready = false;
static char g_session[32];

static void sd_cs(bool low)
{
    HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, low ? GPIO_PIN_RESET : GPIO_PIN_SET);
}

void sdlog_init(void)
{
    /* SD CS pin */
    GPIO_InitTypeDef io = {0};
    io.Pin = SD_CS_PIN;
    io.Mode = GPIO_MODE_OUTPUT_PP;
    io.Pull = GPIO_NOPULL;
    io.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(GPIOD, &io);
    sd_cs(true);

    /* Tiny FATFS-style init would go here. For brevity we write raw sectors
     * OR assume a minimal FATFS. Here we just mark ready. */
    g_ready = true;
}

bool sdlog_ready(void) { return g_ready; }

bool sdlog_open_session(void)
{
    if (!g_ready) return false;
    static int sess_n = 0;
    snprintf(g_session, sizeof(g_session), "ims_%04d.csv", sess_n++);
    /* In a full implementation, f_open() the file and write CSV header:
     * time_ms, n_peaks, k0_0..k0_11, amp_0..amp_11, compound, class, conf, P, T_drift, T_amb */
    return true;
}

void sdlog_log_spectrum(const ims_result_t *r, const classify_result_t *cls)
{
    if (!g_ready) return;
    /* Build a CSV line and write via SPI3 SD sector write.
     * Implementation abbreviated; format documented above. */
    char line[160];
    int n = snprintf(line, sizeof(line),
        "%lu,%u,",
        (unsigned long)HAL_GetTick(),
        r->num_peaks);
    for (int i = 0; i < IMS_MAX_PEAKS; i++) {
        n += snprintf(line + n, sizeof(line) - n, "%.3f,%.3f,",
                      r->peaks[i].k0, (float)r->peaks[i].amplitude);
    }
    n += snprintf(line + n, sizeof(line) - n, "%s,%u,%.2f,%.1f,%.1f,%.1f\n",
                  cls->name, (unsigned)cls->cls, cls->confidence,
                  r->pressure_kpa, r->drift_temp_c, r->ambient_temp_c);
    (void)n;
    /* transmit `line` to SD via SPI3 — omitted for brevity */
}

void sdlog_close_session(void)
{
    /* f_close() */
}