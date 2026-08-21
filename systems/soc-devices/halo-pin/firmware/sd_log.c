/*
 * sd_log.c — microSD FAT32 CSV logging via SPI2
 *
 * Format: one CSV row per minute with timestamp, flow, T, RH, P,
 * 16-bin counts, PM1, PM2.5, PM10.
 *
 * SPI2: PB12=CS, PB13=SCK, PB14=MISO, PB15=MOSI
 */

#include "sd_log.h"
#include "stm32g474_conf.h"
#include <string.h>
#include <stdio.h>

static bool sd_ok = false;

static void spi2_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    /* PB13=SCK, PB14=MISO, PB15=MOSI → AF5 (SPI2) */
    GPIOB->AFR[1] &= ~(GPIO_AFRH_AFSEL13 | GPIO_AFRH_AFSEL14 | GPIO_AFRH_AFSEL15);
    GPIOB->AFR[1] |= (5u << GPIO_AFRH_AFSEL13_Pos)
                   | (5u << GPIO_AFRH_AFSEL14_Pos)
                   | (5u << GPIO_AFRH_AFSEL15_Pos);
    GPIOB->MODER = (GPIOB->MODER & ~(GPIO_MODER_MODE13 | GPIO_MODER_MODE14 | GPIO_MODER_MODE15))
                 | (2u << GPIO_MODER_MODE13_Pos)
                 | (2u << GPIO_MODER_MODE14_Pos)
                 | (2u << GPIO_MODER_MODE15_Pos);
    /* PB12 = CS (manual GPIO) */
    GPIOB->MODER = (GPIOB->MODER & ~GPIO_MODER_MODE12) | (1u << GPIO_MODER_MODE12_Pos);
    GPIOB->BSRR = GPIO_BSRR_BS12;  /* CS high */

    RCC->APB1ENR1 |= RCC_APB1ENR1_SPI2EN;
    SPI2->CR1 = SPI_CR1_MSTR | SPI_CR1_BR_1 | SPI_CR1_BR_0   /* clk/32 ~5 MHz */
              | SPI_CR1_SSM | SPI_CR1_SSI | SPI_CR1_SPE;
}

static uint8_t spi_xfer(uint8_t tx)
{
    SPI2->DR = tx;
    while (!(SPI2->SR & SPI_SR_RXNE)) ;
    return (uint8_t)SPI2->DR;
}

void sd_log_init(void)
{
    spi2_init();
    /* A full SD card init is complex; in real firmware use FatFs. */
    sd_ok = true;
}

void sd_log_minute(uint16_t id, float dt_s, float vol_l, float flow_lpm,
                    float temp_c, float rh_pct, float pres_hpa,
                    const uint32_t *counts, uint8_t n,
                    float pm1, float pm25, float pm10)
{
    if (!sd_ok) return;
    /* Build CSV line (in real firmware: FatFs f_write) */
    char line[256];
    int pos = snprintf(line, sizeof(line),
                       "%u,%.1f,%.3f,%.2f,%.1f,%.1f,%.1f",
                       id, dt_s, vol_l, flow_lpm, temp_c, rh_pct, pres_hpa);
    for (uint8_t i = 0; i < n; ++i)
        pos += snprintf(line + pos, sizeof(line) - pos, ",%lu", (unsigned long)counts[i]);
    pos += snprintf(line + pos, sizeof(line) - pos,
                    ",%.1f,%.1f,%.1f\r\n", pm1, pm25, pm10);
    /* In real firmware, write to FatFs file handle here */
    (void)line;
}

void sd_log_flush(void) { /* FatFs f_sync in real firmware */ }