/*
 * storage.c — MicroSD CSV + binary logging
 *
 * CSV: time_ms, disp_nm, vel_mms (up to 25 ksps)
 * Binary: raw I/Q int16 pairs (up to 2.5 Msps)
 * Also stores user params in a small INI-style file.
 */

#include "storage.h"
#include "stm32g4xx_hal.h"
#include <string.h>
#include <stdio.h>

extern SPI_HandleTypeDef hspi2;

#define SD_CS_PORT  GPIOB
#define SD_CS_PIN   GPIO_PIN_12

static void sd_cs_low(void)  { HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, GPIO_PIN_RESET); }
static void sd_cs_high(void) { HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, GPIO_PIN_SET); }

/* FatFs handle */
static FATFS s_fat;
static FIL   s_file;
static uint8_t s_mounted = 0;

void storage_init(void)
{
    sd_cs_high();
    if (f_mount(&s_fat, "", 1) == FR_OK) {
        s_mounted = 1;
    }
}

void storage_log_csv(const phase_block_t *pb, uint32_t t_ms)
{
    if (!s_mounted) return;
    if (f_open(&s_file, "vibra.csv", FA_OPEN_APPEND | FA_WRITE) != FR_OK) return;

    char line[48];
    for (uint32_t i = 0; i < pb->n; i++) {
        int len = snprintf(line, sizeof(line), "%u,%.2f,%.4f\r\n",
                           (unsigned)(t_ms + i),
                           pb->disp_nm[i],
                           pb->vel_mms[i]);
        UINT bw;
        f_write(&s_file, line, len, &bw);
    }
    f_close(&s_file);
}

void storage_log_iq_bin(const iq_block_t *iq, uint32_t t_ms)
{
    if (!s_mounted) return;
    if (f_open(&s_file, "vibra.iq", FA_OPEN_APPEND | FA_WRITE) != FR_OK) return;

    /* Header: 4-byte time, 4-byte count */
    UINT bw;
    f_write(&s_file, &t_ms, sizeof(t_ms), &bw);
    uint32_t n = iq->n;
    f_write(&s_file, &n, sizeof(n), &bw);
    /* Interleaved int16 I,Q pairs */
    for (uint32_t i = 0; i < iq->n; i++) {
        f_write(&s_file, &iq->i[i], sizeof(int16_t), &bw);
        f_write(&s_file, &iq->q[i], sizeof(int16_t), &bw);
    }
    f_close(&s_file);
}

void storage_load_params(acq_params_t *p)
{
    if (!s_mounted) return;
    if (f_open(&s_file, "vibra.cfg", FA_READ) != FR_OK) return;
    UINT br;
    f_read(&s_file, p, sizeof(*p), &br);
    f_close(&s_file);
}

void storage_save_params(const acq_params_t *p)
{
    if (!s_mounted) return;
    if (f_open(&s_file, "vibra.cfg", FA_CREATE_ALWAYS | FA_WRITE) != FR_OK) return;
    UINT bw;
    f_write(&s_file, p, sizeof(*p), &bw);
    f_close(&s_file);
}

void storage_sync(void)
{
    if (s_mounted) f_sync(&s_file);
}