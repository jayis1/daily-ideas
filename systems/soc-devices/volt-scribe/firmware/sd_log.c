/*
 * volt-scribe — sd_log.c
 * MicroSD card logging via SPI (FAT32 filesystem)
 */

#include "sd_log.h"
#include <stdio.h>
#include <string.h>

extern SPI_HandleTypeDef hspi1;

#define SD_CS_LOW()   HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_RESET)
#define SD_CS_HIGH()  HAL_GPIO_WritePin(GPIOA, GPIO_PIN_11, GPIO_PIN_SET)

static int log_sequence = 0;
static char current_filename[32];
static int file_open = 0;

/* ── FatFS integration (placeholder — uses STM32 FatFs middleware) ─ */

void sdlog_init(void)
{
    /* FatFS initialization via STM32 middleware */
    /* f_mount(&SDFatFS, "", 1); */
    log_sequence = 0;
}

int sdlog_open(const char *prefix)
{
    snprintf(current_filename, sizeof(current_filename), "%s_%06d.csv", prefix, log_sequence);
    file_open = 1;
    /* In production: f_open(&SDFile, current_filename, FA_WRITE | FA_CREATE_ALWAYS); */
    return 0;
}

int sdlog_write(const char *data)
{
    if (!file_open) return -1;
    /* In production: f_write(&SDFile, data, strlen(data), &bytes_written); */
    /* Also echo to UART for debugging */
    printf("%s", data);
    return 0;
}

int sdlog_close(const char *filename)
{
    file_open = 0;
    log_sequence++;
    /* In production: f_close(&SDFile); */
    return 0;
}

int sdlog_get_sequence(void)
{
    return log_sequence;
}

const char *sdlog_get_filename(void)
{
    return current_filename;
}