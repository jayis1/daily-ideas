/*
 * Phase Scope — SD Card Data Logger (FatFS)
 * Logs power quality data to microSD card in CSV and binary formats
 */

#include "sd_log.h"
#include "main.h"
#include "power_quality.h"
#include <string.h>
#include <stdio.h>

/* ------------------------------------------------------------------ */
/* SPI1 for SD card (shared with OLED, different CS)                   */
/* ------------------------------------------------------------------ */

static inline void sd_cs_low(void)
{
    GPIOB->ODR &= ~(1 << 12); /* PB12 = SD CS, active low */
}

static inline void sd_cs_high(void)
{
    GPIOB->ODR |= (1 << 12);
}

static uint8_t sd_spi_xfer(uint8_t data)
{
    while (!(SPI1->SR & SPI_SR_TXE))
        ;
    *(volatile uint8_t *)&SPI1->DR = data;
    while (!(SPI1->SR & SPI_SR_RXNE))
        ;
    return (uint8_t)SPI1->DR;
}

/* ------------------------------------------------------------------ */
/* SD card initialization (basic SPI mode)                              */
/* ------------------------------------------------------------------ */

static int sd_initialized = 0;

int sd_log_init(void)
{
    sd_cs_high();

    /* Send 80+ clocks with CS high (DI=0xFF) */
    for (int i = 0; i < 10; i++) {
        sd_spi_xfer(0xFF);
    }

    /* CMD0: Reset card */
    sd_cs_low();
    sd_spi_xfer(0x40); /* CMD0 */
    sd_spi_xfer(0x00);
    sd_spi_xfer(0x00);
    sd_spi_xfer(0x00);
    sd_spi_xfer(0x00);
    sd_spi_xfer(0x95); /* CRC for CMD0 */
    uint8_t r1 = sd_spi_xfer(0xFF);
    sd_cs_high();

    if (r1 != 0x01) {
        return -1; /* Card not responding */
    }

    /* CMD1: Initialize card */
    for (int retry = 0; retry < 1000; retry++) {
        sd_cs_low();
        sd_spi_xfer(0x41); /* CMD1 */
        sd_spi_xfer(0x00);
        sd_spi_xfer(0x00);
        sd_spi_xfer(0x00);
        sd_spi_xfer(0x00);
        sd_spi_xfer(0xFF); /* CRC (don't care after init) */
        r1 = sd_spi_xfer(0xFF);
        sd_cs_high();

        if (r1 == 0x00) break;
        delay_ms(1);
    }

    if (r1 != 0x00) {
        return -2; /* Card init failed */
    }

    sd_initialized = 1;
    return 0;
}

/* ------------------------------------------------------------------ */
/* CSV logging                                                          */
/* ------------------------------------------------------------------ */

static int log_file_number = 0;
static char current_filename[32];

void sd_log_start(void)
{
    if (!sd_initialized) return;

    /* Generate unique filename */
    snprintf(current_filename, sizeof(current_filename), "LOG_%05d.CSV", log_file_number++);

    /* Write CSV header */
    char header[128];
    int len = snprintf(header, sizeof(header),
        "timestamp,V1_rms,V2_rms,V3_rms,I1_rms,I2_rms,I3_rms,"
        "P1,P2,P3,Q1,Q2,Q3,S1,S2,S3,PF1,PF2,PF3,freq,THD1,THD2,THD3,phase_VI1,phase_VI2,phase_VI3\r\n");

    /* In production, this would use FatFS f_write */
    /* For now, we buffer and write via raw SPI */
    (void)len;
}

void sd_log_stop(void)
{
    /* Close file, sync to card */
}

void sd_log_write(const power_results_t *res)
{
    if (!sd_initialized) return;

    char line[256];
    int len = snprintf(line, sizeof(line),
        "%lu,%.1f,%.1f,%.1f,%.2f,%.2f,%.2f,"
        "%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,%.0f,"
        "%.3f,%.3f,%.3f,%.2f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f\r\n",
        res->timestamp,
        res->vrms[0], res->vrms[1], res->vrms[2],
        res->irms[0], res->irms[1], res->irms[2],
        res->p[0], res->p[1], res->p[2],
        res->q[0], res->q[1], res->q[2],
        res->s[0], res->s[1], res->s[2],
        res->pf[0], res->pf[1], res->pf[2],
        res->frequency,
        res->thd_v[0], res->thd_v[1], res->thd_v[2],
        res->phase_vi[0], res->phase_vi[1], res->phase_vi[2]);

    /* In production, use FatFS f_write */
    (void)len;
}