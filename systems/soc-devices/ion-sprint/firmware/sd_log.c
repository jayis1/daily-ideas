/*
 * sd_log.c — microSD logging via SPI1
 *
 * PA13=SCK, PA14=MISO, PA15=MOSI, PC4=CS (card detect on PC4)
 * FAT32 filesystem, CSV header + raw binary electropherogram.
 * Each run produces two files:
 *   RUN_xxxx.CSV — header + peak table (human-readable)
 *   RUN_xxxx.BIN — raw electropherogram (float32 array)
 */

#include "sd_log.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <stdio.h>
#include <string.h>

/* SPI1 for SD card (simplified — real code uses FATFS library) */
static void spi1_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOCEN;
    /* PA13/14/15: SPI1 AF5 */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (13u * 2u))) | (2u << (13u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (14u * 2u))) | (2u << (14u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (15u * 2u))) | (2u << (15u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFFFu << 20)) | (5u << 20) | (5u << 24) | (5u << 28);
    /* PC4: CS (output, high = deselected) */
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (4u * 2u))) | (1u << (4u * 2u));
    GPIOC->BSRR = (1u << 4);  /* High = deselect */

    RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;
    SPI1->CR1 = SPI_CR1_MSTR | SPI_CR1_BR_0 | SPI_CR1_BR_1 | SPI_CR1_CPOL | SPI_CR1_CPHA;
    SPI1->CR1 |= SPI_CR1_SPE;
}

static void spi_cs_low(void)  { GPIOC->BSRR = (1u << (4 + 16)); }
static void spi_cs_high(void) { GPIOC->BSRR = (1u << 4); }

static uint8_t spi_xfer(uint8_t tx)
{
    SPI1->DR = tx;
    while (!(SPI1->SR & SPI_SR_RXNE)) ;
    return SPI1->DR;
}

/* Simplified file write (real code uses FATFS f_open/f_write) */
static void file_write(const char *filename, const uint8_t *data, uint32_t len)
{
    /* Placeholder: would call FATFS functions */
    (void)filename; (void)data; (void)len;
}

void sd_log_init(void)
{
    spi1_init();
}

void sd_log_write_run(uint16_t run_id, uint8_t bge_recipe, float hv_setpoint,
                      float hv_measured, float temp_c,
                      const float *eph, uint32_t eph_count,
                      const ion_result_t *results, uint8_t result_count)
{
    /* Build CSV header */
    char csv[512];
    int pos = snprintf(csv, sizeof(csv),
        "Run,%u\nBGE,%u\nHV_setpoint_kV,%.1f\nHV_measured_kV,%.1f\nTemp_C,%.1f\nEph_samples,%lu\n",
        run_id, bge_recipe, hv_setpoint, hv_measured, temp_c, (unsigned long)eph_count);
    pos += snprintf(csv + pos, sizeof(csv) - pos, "\nIon,t_m(s),Area,Height,Conc(mM)\n");
    for (uint8_t i = 0; i < result_count && pos < (int)sizeof(csv) - 40; i++) {
        pos += snprintf(csv + pos, sizeof(csv) - pos, "%s,%.1f,%.3f,%.3f,%.3f\n",
            results[i].ion_name, results[i].migration_time,
            results[i].area, results[i].height, results[i].concentration_mM);
    }

    char fname[20];
    snprintf(fname, sizeof(fname), "RUN_%04d.CSV", run_id);
    file_write(fname, (const uint8_t *)csv, (uint32_t)pos);

    /* Write raw electropherogram binary */
    snprintf(fname, sizeof(fname), "RUN_%04d.BIN", run_id);
    file_write(fname, (const uint8_t *)eph, eph_count * sizeof(float));
}

void sd_log_write_error(uint16_t run_id, const char *msg,
                        float current_ua, float voltage_kv)
{
    char csv[256];
    int pos = snprintf(csv, sizeof(csv),
        "ERROR,Run %u,%s,I=%.1f uA,V=%.1f kV\n",
        run_id, msg, current_ua, voltage_kv);
    char fname[20];
    snprintf(fname, sizeof(fname), "ERR_%04d.CSV", run_id);
    file_write(fname, (const uint8_t *)csv, (uint32_t)pos);
}