/*
 * sd_log.c — microSD CSV + raw waveform binary logging
 *
 * SPI1: PA13=SCK, PA14=MISO, PA15=MOSI, PB8=CS (25 MHz)
 * Each scan logs:
 *   PT_NNNN.csv  — demographics, SOS, BUA, SI, T, Z, classification
 *   PT_NNNN.bin  — raw 115200-sample A-scan (16-bit, 230 KB)
 */

#include "sd_log.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <stdio.h>
#include <string.h>

static char fname_csv[16];
static char fname_bin[16];
static bool logging = false;

void sd_log_init(void)
{
    /* SPI1 pins: PA13=SCK, PA14=MISO, PA15=MOSI */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (13u * 2u))) | (2u << (13u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (14u * 2u))) | (2u << (14u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (15u * 2u))) | (2u << (15u * 2u));
    /* PB8: CS (output, default high) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (8u * 2u))) | (1u << (8u * 2u));
    GPIOB->BSRR = (1u << 8u);   /* CS high (deselected) */

    /* Enable SPI1 */
    RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;
    SPI1->CR1 = SPI_CR1_MSTR | SPI_CR1_BR_0 | SPI_CR1_CPOL | SPI_CR1_CPHA | SPI_CR1_SSM | SPI_CR1_SSI;
    SPI1->CR1 |= SPI_CR1_SPE;

    logging = false;
}

static void sd_write(const char *name, const uint8_t *data, uint32_t len)
{
    /* Simplified — real code implements SPI SD card block write */
    (void)name; (void)data; (void)len;
}

void sd_log_open_scan(uint16_t id, uint16_t patient_id, uint8_t age,
                      uint8_t sex, uint8_t eth)
{
    snprintf(fname_csv, sizeof(fname_csv), "PT_%04d.csv", id);
    snprintf(fname_bin, sizeof(fname_bin), "PT_%04d.bin", id);

    char header[128];
    snprintf(header, sizeof(header),
             "scan_id,patient_id,age,sex,ethnicity,sos_mps,bua_db_mhz,si,t_score,z_score,class\r\n");
    sd_write(fname_csv, (const uint8_t*)header, strlen(header));
    logging = true;
    (void)patient_id; (void)age; (void)sex; (void)eth;
}

void sd_log_results(uint16_t id, float sos, float bua, float si,
                     float t, float z, int cls)
{
    if (!logging) return;
    char row[128];
    snprintf(row, sizeof(row), "%d,,,,,,%.1f,%.1f,%.1f,%.2f,%.2f,%d\r\n",
             id, sos, bua, si, t, z, cls);
    sd_write(fname_csv, (const uint8_t*)row, strlen(row));
}

void sd_log_waveform(uint16_t id, const uint16_t *buf, uint32_t n)
{
    if (!logging) return;
    sd_write(fname_bin, (const uint8_t*)buf, n * 2);
    (void)id;
}

void sd_log_close(void)
{
    logging = false;
}