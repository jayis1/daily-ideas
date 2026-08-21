/*
 * aux_adc.c — ADS1115 16-bit aux ADC over I2C (PA11/PA12, shared with OLED)
 *
 * The ADS1115 is a 4-channel 16-bit delta-sigma ADC at up to 860 sps,
 * address 0x48 on the I2C bus. Used for slow aux inputs (thermistor,
 * temperature, B-field hall-sensor, etc.). Single-shot mode.
 */

#include "stm32g491_conf.h"
#include "aux_adc.h"
#include "i2c.h"

#define ADS_ADDR   0x48
#define REG_CONV   0x00
#define REG_CFG    0x01

void aux_adc_init(void)
{
    /* ADS1115 power-on default: single-shot, ±4.096 V, 128 sps */
}

static uint16_t read_reg16(uint8_t reg)
{
    uint8_t w[1] = { reg };
    i2c_write(ADS_ADDR, w, 1);
    uint8_t r[2];
    i2c_read(ADS_ADDR, r, 2);
    return ((uint16_t)r[0] << 8) | r[1];
}

static void write_reg16(uint8_t reg, uint16_t val)
{
    uint8_t w[3] = { reg, (uint8_t)(val >> 8), (uint8_t)(val & 0xFF) };
    i2c_write(ADS_ADDR, w, 3);
}

float aux_adc_read(uint8_t channel)
{
    if (channel > 3) return 0.0f;
    /* Config: single-shot, channel, ±4.096 V, 128 sps, start */
    uint16_t cfg = (1U << 15)                /* OS = start */
                 | ((channel & 0x7U) << 12)  /* MUX single-ended */
                 | (1U << 9)                 /* PGA = ±4.096 V */
                 | (4U << 5)                 /* 128 sps */
                 | (1U << 0);                /* single-shot */
    write_reg16(REG_CFG, cfg);
    /* Wait for conversion (≈8 ms at 128 sps) */
    for (volatile int i = 0; i < 200000; ++i) ;
    int16_t raw = (int16_t)read_reg16(REG_CONV);
    /* ±4.096 V / 32768 = 125 µV/LSB */
    return (float)raw * 0.000125f;
}

float aux_adc_read_diff01(void)
{
    uint16_t cfg = (1U << 15) | (0U << 12) | (1U << 9) | (4U << 5) | (1U << 0);
    write_reg16(REG_CFG, cfg);
    for (volatile int i = 0; i < 200000; ++i) ;
    int16_t raw = (int16_t)read_reg16(REG_CONV);
    return (float)raw * 0.000125f;
}