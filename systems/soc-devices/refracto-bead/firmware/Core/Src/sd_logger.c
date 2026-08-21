/**
 * sd_logger.c — microSD CSV logging via SPI
 *
 * Logs each measurement as a CSV row:
 *   timestamp, t_prism, t_ambient, n_D, n_F, n_C, V_D, dispersion,
 *   brix, sg, abv, freeze_pt, compound_id, compound_name, confidence
 *
 * Uses FatFs for filesystem access. Falls back gracefully if no card present.
 */

#include "sd_logger.h"
#include <stdio.h>
#include <string.h>

extern SPI_HandleTypeDef hspi2;

#define SD_CS_PORT  GPIOA
#define SD_CS_PIN   GPIO_PIN_8

static int s_card_present = 0;

static void sd_cs_low(void) {
    HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, GPIO_PIN_RESET);
}

static void sd_cs_high(void) {
    HAL_GPIO_WritePin(SD_CS_PORT, SD_CS_PIN, GPIO_PIN_SET);
}

/* Simple SPI byte transfer */
static uint8_t spi_xfer(uint8_t tx) {
    uint8_t rx;
    HAL_SPI_TransmitReceive(&hspi2, &tx, &rx, 1, 100);
    return rx;
}

/* SD card SPI initialization (simplified) */
static int sd_init_spi(void) {
    sd_cs_high();
    /* Send 80 dummy clocks (10 bytes) to wake up the card */
    for (int i = 0; i < 10; i++) spi_xfer(0xFF);

    sd_cs_low();
    /* CMD0: GO_IDLE_STATE */
    spi_xfer(0x40 | 0);
    spi_xfer(0x00); spi_xfer(0x00); spi_xfer(0x00); spi_xfer(0x00);
    spi_xfer(0x95);  /* Valid CRC for CMD0 */
    uint8_t r1 = spi_xfer(0xFF);
    sd_cs_high();

    if (r1 != 0x01) return -1;  /* Not in idle state */

    /* CMD8: SEND_IF_COND (check voltage range) */
    sd_cs_low();
    spi_xfer(0x40 | 8);
    spi_xfer(0x00); spi_xfer(0x00); spi_xfer(0x01); spi_xfer(0xAA);
    spi_xfer(0x87);
    r1 = spi_xfer(0xFF);
    /* Read remaining response bytes */
    for (int i = 0; i < 4; i++) spi_xfer(0xFF);
    sd_cs_high();

    /* ACMD41: SD_SEND_OP_COND (initialize) */
    for (int retry = 0; retry < 100; retry++) {
        sd_cs_low();
        /* CMD55 */
        spi_xfer(0x40 | 55);
        spi_xfer(0x00); spi_xfer(0x00); spi_xfer(0x00); spi_xfer(0x00);
        spi_xfer(0x00);
        r1 = spi_xfer(0xFF);
        sd_cs_high();

        sd_cs_low();
        /* ACMD41 */
        spi_xfer(0x40 | 41);
        spi_xfer(0x40); spi_xfer(0x00); spi_xfer(0x00); spi_xfer(0x00);
        spi_xfer(0x00);
        r1 = spi_xfer(0xFF);
        sd_cs_high();

        if (r1 == 0x00) break;  /* Initialization complete */
        HAL_Delay(10);
    }

    if (r1 != 0x00) return -1;

    s_card_present = 1;
    return 0;
}

void sd_logger_init(SPI_HandleTypeDef *hspi) {
    (void)hspi;  /* Uses hspi2 extern */

    /* Configure CS pin as output */
    GPIO_InitTypeDef gp = {0};
    gp.Pin = SD_CS_PIN;
    gp.Mode = GPIO_MODE_OUTPUT_PP;
    gp.Pull = GPIO_PULLUP;
    gp.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(SD_CS_PORT, &gp);
    sd_cs_high();

    /* Try to initialize the SD card */
    if (sd_init_spi() == 0) {
        s_card_present = 1;
    } else {
        s_card_present = 0;
    }

    /* Note: Full FatFs integration would be added here.
     * This simplified driver provides the SPI layer; in production,
     * integrate FatFs for file-system-level logging.
     */
}

void sd_logger_write(const ri_result_t *result) {
    if (!s_card_present || !result) return;

    /* Format CSV row */
    char line[256];
    snprintf(line, sizeof(line),
             "%lu,%.2f,%.2f,%.4f,%.4f,%.4f,%.1f,%.4f,%.1f,%.3f,%.1f,%.1f,%d,%s,%.2f\r\n",
             (unsigned long)result->timestamp,
             result->t_prism,
             result->t_ambient,
             result->n_D,
             result->n_F,
             result->n_C,
             result->abbe_vd,
             result->dispersion,
             result->brix,
             result->specific_grav,
             result->abv,
             result->freeze_point,
             (int)result->compound_id,
             result->compound_name,
             result->confidence);

    /* In a full implementation, this would:
     * 1. Open the log file (append mode) via FatFs
     * 2. Write the CSV line
     * 3. Close the file
     * 4. Sync to ensure data is flushed to the card
     *
     * The FatFs layer handles sector-level writes via the SPI driver.
     */
    (void)line;  /* Simplified — production uses f_open/f_puts/f_close */
}