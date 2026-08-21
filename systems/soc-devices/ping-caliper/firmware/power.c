/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * power.c — Power management, rail gating, fuel gauge, charge status
 *
 * Controls the HV boost converter enable, the analog front-end (VDDA)
 * rail gate, and MicroSD power gate. Reads battery state-of-charge from
 * the MAX17048 fuel gauge over I²C and the charge status from the TP4056.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "power.h"
#include <string.h>

static power_t g_power;

/* ---- I²C helpers (for MAX17048 at address 0x36) ---- */
#define MAX17048_ADDR   0x36
#define I2C_TIMEOUT     1000

static void i2c_init(void)
{
    RCC->APB1ENR1 |= RCC_APB1ENR1_I2C1EN;
    RCC->AHB2ENR  |= RCC_AHB2ENR_GPIOBEN;

    /* PB10 (SCL) and PB11 (SDA) → AF4 (I2C1) */
    GPIOB->MODER = (GPIOB->MODER & ~(GPIO_MODER_MODE10 | GPIO_MODER_MODE11)) |
                   (2U << GPIO_MODER_MODE10_Pos) | (2U << GPIO_MODER_MODE11_Pos);
    GPIOB->OTYPER |= GPIO_OTYPER_OT10 | GPIO_OTYPER_OT11;   /* open-drain */
    GPIOB->AFR[1] = (GPIOB->AFR[1] & ~(0xFF << 8)) |
                    (4U << 8) | (4U << 12);   /* AF4 */

    /* I2C1: 100 kHz, standard mode */
    I2C1->TIMINGR = 0x10B17DB4U;   /* 100 kHz from 170 MHz */
    I2C1->CR1 = I2C_CR1_PE;
}

static uint8_t i2c_read_reg(uint8_t addr, uint8_t reg, uint16_t *out)
{
    /* Write reg, then read 2 bytes. */
    I2C1->CR2 = (uint32_t)(addr << 1) | (1U << 16) | I2C_CR2_START;
    I2C1->TXDR = reg;
    uint32_t t = I2C_TIMEOUT;
    while (!(I2C1->ISR & I2C_ISR_TXIS) && t--) { }
    if (!(I2C1->ISR & I2C_ISR_TXIS)) return 0;
    I2C1->CR2 |= I2C_CR2_STOP;

    /* Restart for read */
    I2C1->CR2 = (uint32_t)(addr << 1) | (2U << 16) | I2C_CR2_RD_WRN | I2C_CR2_START;
    t = I2C_TIMEOUT;
    while (!(I2C1->ISR & I2C_ISR_RXNE) && t--) { }
    if (!(I2C1->ISR & I2C_ISR_RXNE)) return 0;
    uint8_t lo = (uint8_t)I2C1->RXDR;
    t = I2C_TIMEOUT;
    while (!(I2C1->ISR & I2C_ISR_RXNE) && t--) { }
    if (!(I2C1->ISR & I2C_ISR_RXNE)) return 0;
    uint8_t hi = (uint8_t)I2C1->RXDR;
    I2C1->CR2 |= I2C_CR2_STOP;
    *out = (uint16_t)((hi << 8) | lo);
    return 1;
}

void power_init(void)
{
    /* Enable GPIO clocks */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN |
                    RCC_AHB2ENR_GPIOCEN;

    /* Output pins: PA5 (HV enable), PB9 (VDDA gate), PC8 (SD power),
     * PC1 (beeper), PC13 (pulser inhibit), PC10 (charge LED) */
    GPIOA->MODER = (GPIOA->MODER & ~GPIO_MODER_MODE5) |
                   (1U << GPIO_MODER_MODE5_Pos);
    GPIOB->MODER = (GPIOB->MODER & ~GPIO_MODER_MODE9) |
                   (1U << GPIO_MODER_MODE9_Pos);
    GPIOC->MODER = (GPIOC->MODER & ~(GPIO_MODER_MODE1 | GPIO_MODER_MODE8 |
                                      GPIO_MODER_MODE10 | GPIO_MODER_MODE13)) |
                   (1U << GPIO_MODER_MODE1_Pos)  | (1U << GPIO_MODER_MODE8_Pos) |
                   (1U << GPIO_MODER_MODE10_Pos) | (1U << GPIO_MODER_MODE13_Pos);

    /* Input pins: PC9 (VBUS), PC11 (CHRG), PC12 (STDBY), PC3 (tamper) */
    GPIOC->MODER &= ~(GPIO_MODER_MODE9 | GPIO_MODER_MODE11 |
                      GPIO_MODER_MODE12 | GPIO_MODER_MODE3);
    GPIOC->PUPDR |= (1U << GPIO_PUPDR_PUPD9_Pos) |
                    (1U << GPIO_PUPDR_PUPD11_Pos) |
                    (1U << GPIO_PUPDR_PUPD12_Pos);

    /* Start with all rails off (safe) */
    power_enable_hv(0);
    power_enable_afe(0);
    power_enable_sd(0);
    /* Pulser inhibit (PC13) high = inhibited */
    GPIOC->BSRR = (1U << 13);

    i2c_init();

    memset(&g_power, 0, sizeof(g_power));
    g_power.state = POWER_STATE_RUN;
}

void power_update(power_t *pwr)
{
    /* Read battery % + voltage from MAX17048 */
    uint16_t soc, vcell;
    if (i2c_read_reg(MAX17048_ADDR, 0x10, &vcell)) {   /* VCELL register */
        /* VCELL: 78.125 µV/cell per bit → mV = vcell * 78.125 / 1000
         * Simplified: vcell raw ≈ mV / 1.25 */
        g_power.battery_mv = (uint16_t)((uint32_t)vcell * 1250U / 10000U);
    }
    if (i2c_read_reg(MAX17048_ADDR, 0x11, &soc)) {    /* SOC register */
        /* SOC: 1/256 % per bit */
        g_power.battery_pct = (uint8_t)(soc / 256U);
    }

    /* Charge status */
    uint8_t chrg = (GPIOC->IDR & (1U << 11)) ? 0 : 1;   /* CHRG active low */
    uint8_t stdby = (GPIOC->IDR & (1U << 12)) ? 0 : 1;  /* STDBY active low */
    g_power.charging = chrg;
    g_power.vbus_present = (GPIOC->IDR & (1U << 9)) ? 1 : 0;
    (void)stdby;

    if (pwr) *pwr = g_power;
}

void power_set_state(power_state_t state)
{
    g_power.state = state;
    switch (state) {
    case POWER_STATE_RUN:
        power_enable_afe(1);
        break;
    case POWER_STATE_IDLE:
        power_enable_hv(0);
        power_enable_afe(0);
        break;
    case POWER_STATE_SLEEP:
        power_enable_hv(0);
        power_enable_afe(0);
        power_enable_sd(0);
        break;
    case POWER_STATE_CHARGE:
        power_enable_hv(0);
        power_enable_afe(0);
        break;
    }
}

void power_enable_hv(uint8_t en)
{
    if (en) GPIOA->BSRR = (1U << 5);             /* PA5 high (HV on) */
    else    GPIOA->BSRR = (1U << (16 + 5));      /* PA5 low (HV off) */
    g_power.hv_enabled = en ? 1 : 0;
}

void power_enable_afe(uint8_t en)
{
    if (en) GPIOB->BSRR = (1U << 9);             /* PB9 high (AFE on) */
    else    GPIOB->BSRR = (1U << (16 + 9));      /* PB9 low (AFE off) */
    g_power.afe_enabled = en ? 1 : 0;
}

void power_enable_sd(uint8_t en)
{
    if (en) GPIOC->BSRR = (1U << 8);             /* PC8 high (SD on) */
    else    GPIOC->BSRR = (1U << (16 + 8));      /* PC8 low (SD off) */
}

uint8_t power_read_battery(uint8_t *pct, uint16_t *mv)
{
    if (pct) *pct = g_power.battery_pct;
    if (mv)  *mv  = g_power.battery_mv;
    return 1;
}

uint8_t power_read_charge_status(uint8_t *charging, uint8_t *standby)
{
    if (charging) *charging = g_power.charging;
    if (standby)  *standby  = (g_power.vbus_present && !g_power.charging);
    return 1;
}

void power_low_battery_handler(void)
{
    /* Shut down HV + AFE, flash red LED, beep, and transition to sleep. */
    power_enable_hv(0);
    power_enable_afe(0);
    /* Red LED on */
    GPIOB->BSRR = (1U << 7);
    /* Beep */
    GPIOC->BSRR = (1U << 1);
    for (volatile int i = 0; i < 1000000; i++) { __NOP(); }
    GPIOC->BSRR = (1U << (16 + 1));
    power_set_state(POWER_STATE_SLEEP);
}

const power_t *power_get(void) { return &g_power; }