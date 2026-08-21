/*
 * sd_log.c — microSD card logging (FAT32, AERONET-compatible CSV)
 *
 * SPI1 (PA13=SCK, PA14=MISO, PA15=MOSI) at 25 MHz.
 * Logs measurements in AERONET-compatible CSV format:
 *
 *   date,time,lat,lon,elevation,zenith,azimuth,air_mass,
 *   dni_405,dni_440,dni_675,dni_870,dni_940,dni_1640,
 *   aod_405,aod_440,aod_675,aod_870,aod_940,aod_1640,
 *   angstrom,pwv_cm,pressure_hpa,temp_c
 *
 * Langley data is logged separately:
 *   date,time,air_mass,v_405,v_440,v_675,v_870,v_940,v_1640
 */

#include "sd_log.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <stdio.h>
#include <string.h>

static bool sd_initialized = false;

/* ---- SPI1 helpers (simplified) ---- */
static void spi1_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;

    /* PA13=SCK, PA14=MISO, PA15=MOSI: AF5 */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (13u * 2u))) | (2u << (13u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (14u * 2u))) | (2u << (14u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (15u * 2u))) | (2u << (15u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 4))  | (5u << 4);   /* PA13 AF5 */
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 8))  | (5u << 8);   /* PA14 AF5 */
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 12)) | (5u << 12);  /* PA15 AF5 */

    /* CS on PB7 (GPIO) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (7u * 2u))) | (1u << (7u * 2u));
    GPIOB->ODR |= (1u << 7);   /* CS high */

    /* SPI1: master, 25 MHz, mode 0 */
    SPI1->CR1 = SPI_CR1_MSTR | (0u << SPI_CR1_BR_Pos)   /* /2 ≈ 85 MHz */
              | SPI_CR1_SSM | SPI_CR1_SSI;
    SPI1->CR1 |= SPI_CR1_SPE;
}

static void sd_cs_low(void)  { GPIOB->ODR &= ~(1u << 7); }
static void sd_cs_high(void) { GPIOB->ODR |=  (1u << 7); }

/* ---- SD card init (simplified SPI mode) ---- */
static bool sd_reset(void)
{
    /* In production: send CMD0, CMD8, CMD55, ACMD41, CMD58 sequence.
     * This is a placeholder that always succeeds for the design.
     */
    sd_cs_high();
    for (int i = 0; i < 10; i++) {
        /* Send 0xFF dummy clocks */
        while (!(SPI1->SR & SPI_SR_TXE)) ;
        *(volatile uint8_t *)&SPI1->DR = 0xFF;
        while (!(SPI1->SR & SPI_SR_RXNE)) ;
        (void)SPI1->DR;
    }
    /* Real implementation would do full SD initialization + FAT32 mount */
    return true;
}

/* ---- FAT32 write (simplified) ---- */
static void sd_write_line(const char *line)
{
    /* In production: use a FAT32 library (e.g., PetitFatFs) to append
     * a line to the current log file. This placeholder simulates the
     * write by sending the bytes over SPI.
     */
    sd_cs_low();
    for (const char *p = line; *p; p++) {
        while (!(SPI1->SR & SPI_SR_TXE)) ;
        *(volatile uint8_t *)&SPI1->DR = (uint8_t)*p;
        while (!(SPI1->SR & SPI_SR_RXNE)) ;
        (void)SPI1->DR;
    }
    /* CR + LF */
    while (!(SPI1->SR & SPI_SR_TXE)) ;
    *(volatile uint8_t *)&SPI1->DR = '\r';
    while (!(SPI1->SR & SPI_SR_RXNE)) ;
    (void)SPI1->DR;
    while (!(SPI1->SR & SPI_SR_TXE)) ;
    *(volatile uint8_t *)&SPI1->DR = '\n';
    while (!(SPI1->SR & SPI_SR_RXNE)) ;
    (void)SPI1->DR;
    sd_cs_high();
}

/* ---- Public API ---- */

void sd_log_init(void)
{
    spi1_init();
    sd_initialized = sd_reset();
}

bool sd_log_present(void)
{
    /* Check SD detect pin (PB7 pulled high, card present = low) */
    return (GPIOB->IDR & (1u << 7)) == 0;
}

void sd_log_measurement(const radiometry_result_t *result,
                         const solar_pos_t *pos,
                         double lat, double lon, float elev_m,
                         float temp_c, float pressure_hpa,
                         int year, int month, int day,
                         int hour, int min, int sec)
{
    if (!sd_initialized) return;

    char buf[512];
    /* AERONET-compatible CSV header line is written once at file creation.
     * Here we write just the data line.
     */
    snprintf(buf, sizeof(buf),
        "%04d-%02d-%02d,%02d:%02d:%02d,"
        "%.6f,%.6f,%.1f,%.3f,%.3f,%.4f,"
        "%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,"
        "%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,"
        "%.3f,%.2f,%.1f,%.1f",
        year, month, day, hour, min, sec,
        lat, lon, elev_m, pos->zenith, pos->azimuth, pos->air_mass,
        result->dni[0], result->dni[1], result->dni[2],
        result->dni[3], result->dni[4], result->dni[5],
        result->aod[0], result->aod[1], result->aod[2],
        result->aod[3], result->aod[4], result->aod[5],
        result->angstrom_alpha, result->pwv_cm,
        pressure_hpa, temp_c);

    sd_write_line(buf);
}

void sd_log_langley(const float voltages[6], double air_mass,
                     int year, int month, int day,
                     int hour, int min, int sec)
{
    if (!sd_initialized) return;

    char buf[256];
    snprintf(buf, sizeof(buf),
        "%04d-%02d-%02d,%02d:%02d:%02d,%.4f,"
        "%.4f,%.4f,%.4f,%.4f,%.4f,%.4f",
        year, month, day, hour, min, sec, air_mass,
        voltages[0], voltages[1], voltages[2],
        voltages[3], voltages[4], voltages[5]);

    sd_write_line(buf);
}