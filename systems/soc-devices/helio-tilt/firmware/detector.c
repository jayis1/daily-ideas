/*
 * detector.c — ADS122U04 24-bit ADC + thermopile detector
 *
 * ADS122U04 is configured via SPI3 (PA2=SCK, PA3=MISO, PA4=MOSI, PA1=CS).
 * Data-ready on PA3 (shared with MISO in DIN/DOUT mode, or separate DRDY).
 * START pin on PA5 triggers conversions.
 *
 * Configuration:
 *   - Input: AIN0 (thermopile+) – AIN1 (thermopile−), differential
 *   - PGA: 8× (default), configurable 1–128×
 *   - Data rate: 20 Hz (low noise)
 *   - Voltage reference: external 3.3V (LP5907 analog rail)
 *   - Temperature sensor: internal (cold junction compensation)
 *
 * Thermopile sensitivity: ~50 µV/(W/m²)
 *   At DNI=1400 W/m² → 70 mV → with PGA=8, ADC input = 70mV×8 = 560 mV
 *   → fits in 3.3V reference with margin.
 *   At PGA=128: LSB = 3.3V/(128×2^23) = 0.0031 µV → 0.00006 W/m² (theoretical).
 */

#include "detector.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <string.h>

/* ---- Calibration constants (V₀ per wavelength, from Langley) ---- */
static float v0_calibration[WL_COUNT] = {
    1.0f, 1.0f, 1.0f, 1.0f, 1.0f, 1.0f   /* Defaults, replaced by Langley */
};

static uint8_t current_pga = ADC_PGA_DEFAULT;

/* ---- SPI3 helpers ---- */
static void spi3_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_SPI3EN;

    /* PA1=CS (GPIO), PA2=SCK, PA3=MISO, PA4=MOSI (AF6 for SPI3) */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (1u * 2u))) | (1u << (1u * 2u));  /* CS output */
    GPIOA->ODR |= (1u << 1);   /* CS high (deselected) */

    GPIOA->MODER = (GPIOA->MODER & ~(3u << (2u * 2u))) | (2u << (2u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (3u * 2u))) | (2u << (3u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (4u * 2u))) | (2u << (4u * 2u));
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFu << 8))  | (6u << 8);   /* PA2 AF6 */
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFu << 12)) | (6u << 12);  /* PA3 AF6 */
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFu << 16)) | (6u << 16);  /* PA4 AF6 */

    /* PA5 = START/SYNC (GPIO output) */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (5u * 2u))) | (1u << (5u * 2u));
    GPIOA->ODR &= ~(1u << 5);   /* START low initially */

    /* SPI3: master, 2 MHz, CPOL=0, CPHA=1 (mode 1) */
    SPI3->CR1 = SPI_CR1_MSTR | (15u << SPI_CR1_BR_Pos)   /* /32 ≈ 5.3 MHz */
              | SPI_CR1_CPOL | SPI_CR1_CPHA
              | SPI_CR1_SSM | SPI_CR1_SSI;
    SPI3->CR1 |= SPI_CR1_SPE;
}

static void spi3_cs_low(void)
{
    GPIOA->ODR &= ~(1u << 1);
}

static void spi3_cs_high(void)
{
    GPIOA->ODR |= (1u << 1);
}

static uint8_t spi3_xfer(uint8_t tx)
{
    while (!(SPI3->SR & SPI_SR_TXE)) ;
    *(volatile uint8_t *)&SPI3->DR = tx;
    while (!(SPI3->SR & SPI_SR_RXNE)) ;
    return (uint8_t)SPI3->DR;
}

/* ---- ADS122U04 commands ---- */
#define ADS122_CMD_RESET   0x06
#define ADS122_CMD_START   0x08
#define ADS122_CMD_POWERDN 0x02
#define ADS122_CMD_RDATA   0x10
#define ADS122_CMD_RREG    0x20   /* + (reg<<2) */
#define ADS122_CMD_WREG    0x40   /* + (reg<<2) */

/* ---- ADS122U04 register config ---- */
static void ads122_write_reg(uint8_t reg, uint8_t val)
{
    spi3_cs_low();
    spi3_xfer(ADS122_CMD_WREG | (reg << 2));
    spi3_xfer(val);
    spi3_cs_high();
}

static uint8_t ads122_read_reg(uint8_t reg)
{
    spi3_cs_low();
    spi3_xfer(ADS122_CMD_RREG | (reg << 2));
    uint8_t val = spi3_xfer(0xFF);
    spi3_cs_high();
    return val;
}

static void ads122_config(uint8_t pga)
{
    /* Reg 0: Input multiplexer (AINp=AIN0, AINn=AIN1), PGA gain, PGA enabled
     *   bits[7:5] = MUX (000 = AIN0-AIN1)
     *   bits[4:1] = PGA gain (gain >> 1 encoded: 1→000, 2→001, 4→010, ...)
     *   bit[0]    = PGA bypass (0 = PGA enabled)
     */
    uint8_t gain_code = 0;
    if (pga >= 1)  gain_code = 0;
    if (pga >= 2)  gain_code = 1;
    if (pga >= 4)  gain_code = 2;
    if (pga >= 8)  gain_code = 3;
    if (pga >= 16) gain_code = 4;
    if (pga >= 32) gain_code = 5;
    if (pga >= 64) gain_code = 6;
    if (pga >= 128) gain_code = 7;

    ads122_write_reg(0, (gain_code << 1));

    /* Reg 1: Data rate (20 Hz = 0x04), mode (normal), conv mode (single-shot)
     *   bits[7:5] = DR (100 = 20 SPS)
     *   bit[4]    = MODE (0 = normal)
     *   bit[3]    = CM (0 = single-shot)
     *   bits[2:0] = VREF source (000 = internal 2.048V, 100 = external)
     * We use external 3.3V reference (analog rail):
     */
    ads122_write_reg(1, (4u << 5) | (1u << 2));   /* 20 SPS, ext ref on AIN0/AIN1 */

    /* Reg 2: IDAC (no excitation current) */
    ads122_write_reg(2, 0x00);
}

static int32_t ads122_read_data(void)
{
    /* Trigger conversion: START pulse */
    GPIOA->ODR |=  (1u << 5);   /* START high */
    for (volatile int i = 0; i < 100; i++) ;   /* Small delay */
    GPIOA->ODR &= ~(1u << 5);   /* START low */

    /* Wait for DRDY (poll MISO/DRDY pin — simplified: wait fixed time) */
    /* At 20 Hz, conversion takes ~50 ms */
    for (volatile uint32_t i = 0; i < 4000000; i++) ;   /* ~50 ms */

    /* Read 3 bytes of data */
    spi3_cs_low();
    spi3_xfer(ADS122_CMD_RDATA);
    uint8_t b0 = spi3_xfer(0xFF);
    uint8_t b1 = spi3_xfer(0xFF);
    uint8_t b2 = spi3_xfer(0xFF);
    spi3_cs_high();

    /* Sign-extend 24-bit to 32-bit */
    int32_t raw = ((int32_t)b0 << 16) | ((int32_t)b1 << 8) | b2;
    if (raw & 0x800000) raw |= 0xFF000000;   /* Sign extend */
    return raw;
}

/* ---- Public API ---- */

void detector_init(void)
{
    spi3_init();

    /* Reset ADS122U04 */
    spi3_cs_low();
    spi3_xfer(ADS122_CMD_RESET);
    spi3_cs_high();
    for (volatile int i = 0; i < 10000; i++) ;   /* Reset settling */

    ads122_config(current_pga);
}

void detector_set_pga(uint8_t gain)
{
    if (gain < 1) gain = 1;
    if (gain > 128) gain = 128;
    current_pga = gain;
    ads122_config(gain);
}

void detector_read(detector_reading_t *reading)
{
    int32_t raw = ads122_read_data();

    /* Convert raw 24-bit to voltage:
     * V = raw × Vref / (PGA × 2^23)
     */
    float volts = (float)raw * ADC_VREF
                / ((float)current_pga * (float)(1u << 23));
    float uv = volts * 1e6f;

    /* Convert voltage to DNI:
     * DNI = V / sensitivity = V / 50µV/(W/m²) = V / 50e-6
     */
    float dni = volts / THERMOPILE_SENS;

    reading->voltage_uv = uv;
    reading->dni_wm2 = dni;
    reading->pga = current_pga;
    reading->temperature_c = 25.0f;  /* Would read from ADS122U04 temp sensor */
}

void detector_read_avg(detector_reading_t *reading, uint8_t n)
{
    float sum_v = 0.0f, sum_dni = 0.0f;
    for (uint8_t i = 0; i < n; i++) {
        detector_reading_t r;
        detector_read(&r);
        sum_v   += r.voltage_uv;
        sum_dni += r.dni_wm2;
    }
    reading->voltage_uv   = sum_v / n;
    reading->dni_wm2      = sum_dni / n;
    reading->pga          = current_pga;
    reading->temperature_c = 25.0f;
}

float detector_get_calibration(void)
{
    return v0_calibration[0];   /* Simplified: return first wavelength */
}

void detector_set_calibration(float v0, uint8_t wl_index)
{
    if (wl_index < WL_COUNT)
        v0_calibration[wl_index] = v0;
}