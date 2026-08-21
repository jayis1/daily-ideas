/*
 * sdlog.c — FatFS JSON logging
 */

#include "sdlog.h"
#include "stm32g4xx_hal.h"
#include <stdio.h>
#include <string.h>
#include "ff.h"

static FATFS fs;
static bool mounted = false;

int sdlog_init(void)
{
    FRESULT res = f_mount(&fs, "0:", 1);
    mounted = (res == FR_OK);
    return (res == FR_OK) ? 0 : -1;
}

int sdlog_save(const crystal_t *crystal)
{
    if (!mounted) return -1;

    char filename[64];
    snprintf(filename, sizeof(filename), "0:XTAL_%06lu.JSON", crystal->id);

    FIL f;
    FRESULT res = f_open(&f, filename, FA_WRITE | FA_CREATE_ALWAYS);
    if (res != FR_OK) return -1;

    /* Write JSON header */
    f_printf(&f, "{\n");
    f_printf(&f, "  \"id\": %lu,\n", crystal->id);
    f_printf(&f, "  \"f_center_hz\": %.3f,\n", crystal->sweep.f_center_hz);
    f_printf(&f, "  \"timestamp_ms\": %llu,\n", crystal->sweep.timestamp_ms);

    /* Motional parameters */
    if (crystal->params.valid) {
        f_printf(&f, "  \"f_s\": %.6f,\n", crystal->params.f_s);
        f_printf(&f, "  \"R1\": %.3f,\n", crystal->params.R1);
        f_printf(&f, "  \"C1\": %.6e,\n", crystal->params.C1);
        f_printf(&f, "  \"L1\": %.6e,\n", crystal->params.L1);
        f_printf(&f, "  \"C0\": %.6e,\n", crystal->params.C0);
        f_printf(&f, "  \"Q\": %.1f,\n", crystal->params.Q);
        f_printf(&f, "  \"ESR\": %.3f,\n", crystal->params.ESR);
    }

    /* Classification */
    f_printf(&f, "  \"class\": \"%s\",\n", crystal->classification.name);
    f_printf(&f, "  \"confidence\": %.2f,\n", crystal->classification.confidence);

    /* Turnover */
    if (crystal->turnover.valid) {
        f_printf(&f, "  \"T0\": %.2f,\n", crystal->turnover.T0);
        f_printf(&f, "  \"Tc\": %.6f,\n", crystal->turnover.Tc);
    }

    /* Sweep data */
    f_printf(&f, "  \"sweep_points\": %d,\n", crystal->sweep.n_points);
    f_printf(&f, "  \"data\": [\n");
    for (int i = 0; i < crystal->sweep.n_points; i++) {
        f_printf(&f, "    [%.1f, %.6e, %.6e]%s\n",
                 crystal->sweep.points[i].freq_hz,
                 crystal->sweep.points[i].admittance.re,
                 crystal->sweep.points[i].admittance.im,
                 (i < crystal->sweep.n_points - 1) ? "," : "");
    }
    f_printf(&f, "  ]\n");
    f_printf(&f, "}\n");

    f_close(&f);
    return 0;
}

int sdlog_list(int max_entries, uint32_t *ids)
{
    (void)max_entries;
    (void)ids;
    /* TODO: Scan SD card for XTAL_*.JSON files */
    return 0;
}