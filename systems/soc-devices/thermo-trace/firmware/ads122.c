/*
 * ads122.c — ADS122U04 24-bit delta-sigma ADC driver
 *
 * 4-channel SPI communication with the ADS122U04:
 *   CH0: sample PT1000 RTD (differential AIN0-AIN1)
 *   CH1: reference PT1000 RTD (differential AIN2-AIN3)
 *   CH2: heater current sense (single-ended AIN4, via sense resistor)
 *   CH3: supply voltage (AVDD, via internal divider)
 *
 * The ADS122U04 is configured for:
 *   - Internal Vref = 2.048V
 *   - PGA gain = 8 (for RTD signals, ~0.25V range)
 *   - IDAC = 250 µA on AIN0 and AIN2 (for RTD excitation)
 *   - Data rate = 90 SPS (mains-rejectant, ~11ms settling)
 *   - Continuous conversion mode
 *
 * RTD measurement: 4-wire, IDAC excitation through PT1000:
 *   V_rtd = I_idac × R_rtd
 *   R_rtd = V_rtd / I_idac
 *   T = Callendar-Van Dusen equation from R_rtd
 */

#include "stm32g491_conf.h"
#include "ads122.h"
#include "rtd.h"
#include <string.h>

static uint8_t current_gain = ADS_GAIN_8;
static float   vref = 2.048f;

/* ---- SPI helpers ---- */
static void spi_wait_tx(void) {
    while (!(SPI1_SR & (1U << 1))) ; /* TXE */
}

static void spi_wait_rx(void) {
    while (!(SPI1_SR & (1U << 0))) ; /* RXNE */
}

static uint8_t spi_xfer(uint8_t tx) {
    spi_wait_tx();
    *(volatile uint8_t *)&SPI1_DR = tx;
    spi_wait_rx();
    return (uint8_t)SPI1_DR;
}

static void spi_cs_low(void) {
    GPIO_CLR(ADS_CS_PORT, ADS_CS_PIN);
}

static void spi_cs_high(void) {
    GPIO_SET(ADS_CS_PORT, ADS_CS_PIN);
}

/* ---- ADS122U04 register access ---- */
static void ads_write_reg(uint8_t reg, uint8_t val) {
    spi_cs_low();
    spi_xfer(0x40 | (reg << 2));  /* WREG command: 0100 RRxx */
    spi_xfer(val);
    spi_cs_high();
}

static uint8_t ads_read_reg(uint8_t reg) {
    spi_cs_low();
    spi_xfer(0x20 | (reg << 2));  /* RREG command: 0010 RRxx */
    uint8_t val = spi_xfer(0xFF);
    spi_cs_high();
    return val;
}

static void ads_send_command(uint8_t cmd) {
    spi_cs_low();
    spi_xfer(cmd);
    spi_cs_high();
}

static int32_t ads_read_data(void) {
    spi_cs_low();
    uint8_t b0 = spi_xfer(0xFF);
    uint8_t b1 = spi_xfer(0xFF);
    uint8_t b2 = spi_xfer(0xFF);
    spi_cs_high();
    int32_t raw = ((int32_t)b0 << 16) | ((int32_t)b1 << 8) | (int32_t)b2;
    if (raw & 0x800000) raw |= 0xFF000000; /* sign extend */
    return raw;
}

/* ---- DRDY check ---- */
bool ads_is_drdy(void) {
    return !(GPIO_IDR(ADS_DRDY_PORT) & (1U << ADS_DRDY_PIN));
}

/* ---- Init ---- */
void ads_init(void) {
    /* Configure GPIO: PA5 SCK, PA6 MISO, PA7 MOSI (AF5 for SPI1) */
    GPIO_MODER(GPIOA_BASE) &= ~((3U << (5*2)) | (3U << (6*2)) | (3U << (7*2)));
    GPIO_MODER(GPIOA_BASE) |=  (2U << (5*2)) | (2U << (6*2)) | (2U << (7*2));
    GPIO_AFRL(GPIOA_BASE) = (GPIO_AFRL(GPIOA_BASE) & ~((0xF << (5*4)) | (0xF << (6*4)) | (0xF << (7*4))))
                           | (5U << (5*4)) | (5U << (6*4)) | (5U << (7*4));

    /* PA10 CS, PA11 START — push-pull output, default HIGH */
    GPIO_MODER(GPIOA_BASE) |= (1U << (10*2)) | (1U << (11*2));
    GPIO_SET(ADS_CS_PORT, ADS_CS_PIN);
    GPIO_SET(ADS_START_PORT, ADS_START_PIN);

    /* PA12 DRDY — input, pull-up */
    GPIO_MODER(GPIOA_BASE) &= ~(3U << (12*2));
    GPIO_PUPDR(GPIOA_BASE) |= (1U << (12*2));

    /* SPI1: master, CPOL=1 CPHA=1 (mode 3), baud rate = fAPB2/8 = ~21 MHz */
    SPI1_CR1 = 0;
    SPI1_CR1 = (1U << 2)    /* master mode */
             | (1U << 0)    /* CPOL=1 */
             | (1U << 1)    /* CPHA=1 */
             | (3U << 3)    /* BR = fPCLK/8 */
             | (1U << 6);   /* LSBFIRST=0 → MSBFIRST */
    SPI1_CR2 = (1U << 12);  /* FRXTH: RXNE after 8 bits */
    SPI1_CR1 |= (1U << 6);  /* enable SPI1 */

    /* Reset ADS122U04 */
    ads_send_command(0x06);  /* RESET */
    for (volatile int i = 0; i < 10000; i++) ;  /* small delay */

    /* Config0: MUX=AIN0/AIN1, gain=8, PGA enabled */
    ads_write_reg(ADS_REG_CONFIG0, ADS_MUX_AIN0_AIN1 | (current_gain << 1) | 0x01);

    /* Config1: data rate 90 SPS, normal mode, continuous conversion */
    ads_write_reg(ADS_REG_CONFIG1, ADS_DR_90SPS | 0x04);  /* continuous mode */

    /* Config2: internal Vref, IDAC=250µA on AIN0/AIN2 */
    ads_write_reg(ADS_REG_CONFIG2, ADS_VREF_INT | (ADS_IDAC_250UA << 2) | 0x10);

    /* Config3: DRDY on DOUT/DRDY pin, no CRC */
    ads_write_reg(ADS_REG_CONFIG3, 0x00);

    /* Start continuous conversions */
    ads_send_command(0x08);  /* START */
}

void ads_start_conversion(void) {
    ads_send_command(0x08);  /* START */
}

static void ads_set_mux(uint8_t mux) {
    uint8_t cfg0 = ads_read_reg(ADS_REG_CONFIG0);
    cfg0 &= 0xF0;  /* clear mux bits [3:0] */
    cfg0 |= mux;
    cfg0 |= (current_gain << 1);
    cfg0 |= 0x01;  /* PGA bypass = 0 (PGA enabled) */
    ads_write_reg(ADS_REG_CONFIG0, cfg0);
    ads_start_conversion();
    /* Wait for DRDY with timeout */
    for (volatile int i = 0; i < 200000 && !ads_is_drdy(); i++) ;
}

float ads_raw_to_voltage(int32_t raw, uint8_t gain) {
    float gain_val = 1.0f << gain;
    return (float)raw * vref / (gain_val * 8388608.0f);  /* 2^24/2 */
}

void ads_read_all(ads_data_t *data) {
    /* Read all 4 channels sequentially */
    for (int ch = 0; ch < 4; ch++) {
        ads_set_mux(ch);  /* ch 0..3 maps to mux settings */
        while (!ads_is_drdy()) ;
        data->raw[ch] = ads_read_data();
        data->volt[ch] = ads_raw_to_voltage(data->raw[ch], current_gain);
    }

    /* Convert RTD channels to temperature */
    float idac = 250e-6f;  /* 250 µA */
    float r_sample = data->volt[0] / idac;
    float r_ref    = data->volt[1] / idac;
    data->temp[0] = rtd_r_to_temp(r_sample);
    data->temp[1] = rtd_r_to_temp(r_ref);

    /* CH2: heater current (via sense resistor 0.5Ω + op-amp gain 10) */
    /* V_meas = I × R_sense × gain → I = V_meas / (R_sense × gain) */
    data->i_heater = data->volt[2] / (0.5f * 10.0f);

    /* CH3: supply voltage (internal divider ratio 1/4) */
    data->v_supply = data->volt[3] * 4.0f;

    data->drdy = true;
}

void ads_set_idac(uint8_t idac_setting) {
    uint8_t cfg2 = ads_read_reg(ADS_REG_CONFIG2);
    cfg2 &= ~(0x07 << 2);
    cfg2 |= ((idac_setting & 0x07) << 2);
    ads_write_reg(ADS_REG_CONFIG2, cfg2);
}

void ads_calibrate_offset(void) {
    /* System offset calibration: short input → measure → store offset */
    /* For simplicity, we skip actual calibration here; the ADS122U04
       has internal offset calibration via command 0x04 (SELFOCAL) */
    ads_send_command(0x04);  /* self offset calibration */
    for (volatile int i = 0; i < 100000; i++) ;
}