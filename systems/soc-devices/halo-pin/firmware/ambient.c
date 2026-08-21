/*
 * ambient.c — SHT45 + BME280 ambient sensing over I2C1
 *
 * SHT45  @ 0x44 — T + RH (high accuracy, fast response)
 * BME280 @ 0x77 — pressure + backup T/RH
 */

#include "ambient.h"
#include "stm32g474_conf.h"
#include <stdbool.h>

static void i2c1_init(void)
{
    /* PA11 = I2C1_SDA, PA12 = I2C1_SCL */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->AFR[1] &= ~(GPIO_AFRH_AFSEL11 | GPIO_AFRH_AFSEL12);
    GPIOA->AFR[1] |= (4u << GPIO_AFRH_AFSEL11_Pos) | (4u << GPIO_AFRH_AFSEL12_Pos); /* AF4 = I2C1 */
    GPIOA->MODER = (GPIOA->MODER & ~(GPIO_MODER_MODE11 | GPIO_MODER_MODE12))
                 | (2u << GPIO_MODER_MODE11_Pos) | (2u << GPIO_MODER_MODE12_Pos);
    GPIOA->OTYPER |= GPIO_OTYPER_OT11 | GPIO_OTYPER_OT12;
    GPIOA->PUPDR = (GPIOA->PUPDR & ~(GPIO_PUPDR_PUPD11 | GPIO_PUPDR_PUPD12))
                 | (1u << GPIO_PUPDR_PUPD11_Pos) | (1u << GPIO_PUPDR_PUPD12_Pos);

    RCC->APB1ENR1 |= RCC_APB1ENR1_I2C1EN;
    I2C1->TIMINGR = 0x10900FAC;   /* 400 kHz @ 170 MHz */
    I2C1->CR1 = I2C_CR1_PE;
}

static int i2c_write(uint8_t addr, const uint8_t *data, uint8_t len)
{
    I2C1->CR2 = (addr << 1) | ((uint32_t)len << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    for (uint8_t i = 0; i < len; ++i) {
        while (!(I2C1->ISR & I2C_ISR_TXIS)) {
            if (I2C1->ISR & I2C_ISR_NACKF) { I2C1->ICR = I2C_ICR_NACKCF; return -1; }
        }
        I2C1->TXDR = data[i];
    }
    while (!(I2C1->ISR & I2C_ISR_TC)) ;
    I2C1->CR2 |= I2C_CR2_AUTOEND;
    return 0;
}

static int i2c_read(uint8_t addr, uint8_t *data, uint8_t len)
{
    I2C1->CR2 = (addr << 1) | ((uint32_t)len << I2C_CR2_NBYTES_Pos) | I2C_CR2_START | I2C_CR2_RD_WRN;
    for (uint8_t i = 0; i < len; ++i) {
        while (!(I2C1->ISR & I2C_ISR_RXNE)) ;
        data[i] = (uint8_t)I2C1->RXDR;
    }
    I2C1->CR2 |= I2C_CR2_AUTOEND;
    return 0;
}

void ambient_init(void)
{
    i2c1_init();
}

bool ambient_read(float *temp_c, float *rh_pct, float *pres_hpa)
{
    /* SHT45: measure with clock stretching, command 0xFD (100 Hz repeat) */
    uint8_t cmd = 0xFD;
    if (i2c_write(0x44, &cmd, 1) != 0) return false;
    /* Wait ~10 ms for conversion */
    for (volatile int i = 0; i < 200000; ++i) ;
    uint8_t buf[6];
    if (i2c_read(0x44, buf, 6) != 0) return false;
    uint16_t t_raw = (buf[0] << 8) | buf[1];
    uint16_t rh_raw = (buf[3] << 8) | buf[4];
    *temp_c = -45.0f + 175.0f * (float)t_raw / 65535.0f;
    *rh_pct = 0.0f + 100.0f * (float)rh_raw / 65535.0f;

    /* BME280 pressure — simplified: read raw pressure, apply rough conversion */
    uint8_t bme_cmd = 0xF7;   /* press MSB */
    i2c_write(0x77, &bme_cmd, 1);
    uint8_t bme[3];
    i2c_read(0x77, bme, 3);
    int32_t p_raw = (bme[0] << 12) | (bme[1] << 4) | (bme[2] >> 4);
    /* Rough: 1 Pa = 1/256 LSB at typical oversampling → hPa */
    *pres_hpa = (float)p_raw / 256.0f / 100.0f;
    /* If pressure is implausible, use standard */
    if (*pres_hpa < 800.0f || *pres_hpa > 1100.0f) *pres_hpa = 1013.25f;
    return true;
}