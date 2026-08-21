/*
 * sd_log.c — SD card logging via SPI
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Logs measurements to a CSV file and persists custom library entries
 * to a binary file on the SD card. Uses a minimal SPI SD card driver
 * (SDSPI) — in production, use FatFs or a full SPI SD driver.
 */
#include "stm32g4xx_hal.h"
#include <stdio.h>
#include <string.h>
#include "sdkconfig.h"
#include "sd_log.h"
#include "library.h"

extern SPI_HandleTypeDef hspi2;

#define SD_CS_PORT  GPIOB
#define SD_CS_PIN   GPIO_PIN_8

static int sd_initialized = 0;

static void sd_cs_low(void)
{
    HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, GPIO_PIN_RESET);
}

static void sd_cs_high(void)
{
    HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, GPIO_PIN_SET);
}

static uint8_t sd_spi_xfer(uint8_t tx)
{
    uint8_t rx;
    HAL_SPI_TransmitReceive(&hspi2, &tx, &rx, 1, HAL_MAX_DELAY);
    return rx;
}

/* Minimal SD card init (SPI mode) — simplified for illustration */
static int sd_init(void)
{
    /* In production: send 80 dummy clocks, CMD0, CMD8, CMD55+ACMD41, CMD58.
     * Here we just mark as initialized and rely on FatFs in practice. */
    sd_cs_high();
    for (int i = 0; i < 10; i++)
        sd_spi_xfer(0xFF);
    sd_initialized = 1;
    return 0;
}

void sd_log_init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};
    GPIO_InitStruct.Pin   = SD_CS_PIN;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_PULLUP;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(SD_CS_PORT, &GPIO_InitStruct);
    sd_cs_high();
    sd_init();
}

void sd_log_measurement(double rotation, double concentration,
                         const char *compound, double confidence,
                         double temperature, double wavelength)
{
    if (!sd_initialized) return;

    /* In production, use FatFs f_open/f_printf/f_close.
     * Format: timestamp_ms,rotation,concentration,compound,confidence,temp,wavelength */
    char line[128];
    uint32_t ts = HAL_GetTick();
    snprintf(line, sizeof(line), "%lu,%.4f,%.3f,%s,%.1f,%.1f,%.0f\r\n",
             (unsigned long)ts, rotation, concentration,
             compound ? compound : "", confidence, temperature, wavelength);

    /* Write to SD card (FatFs f_write in production) */
    /* sd_log_write_line(line); — implemented with FatFs in full firmware */
}

void sd_log_save_library(const library_entry_t *entries, int count)
{
    if (!sd_initialized || count <= 0) return;
    /* In production: FatFs f_open(SD_LIBRARY_FILENAME, "wb"),
     * f_write(&count, sizeof(int), ...),
     * f_write(entries, sizeof(library_entry_t) * count, ...),
     * f_close() */
}

void sd_log_load_library(library_entry_t *entries, int max, int *count)
{
    if (!sd_initialized) { *count = 0; return; }
    /* In production: FatFs f_open(SD_LIBRARY_FILENAME, "rb"),
     * f_read(&count, sizeof(int), ...),
     * f_read(entries, min(count, max) * sizeof(library_entry_t), ...),
     * f_close() */
    *count = 0;
}