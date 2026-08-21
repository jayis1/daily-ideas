/*
 * airflow.c — sample-airflow blower control + flow-rate monitor
 *
 * Hardware:
 *   PB0  (TIM2_CH3 PWM) ─▶ blower motor driver (DRV8312 input)
 *   PB1  (GPIO input)   ◀─ blower tachometer (for backup RPM)
 *   I2C3 (PA8/PA9 alt)  ◀─ Sensirion SDP810 differential-pressure sensor
 *
 * Flow = K * sqrt(dP), where K is calibrated from the flow restrictor
 * geometry. The SDP810 reports dP in Pa at up to 120 Hz over I2C.
 * A PI controller adjusts blower PWM to hold 1.0 L/min.
 */

#include "airflow.h"
#include "stm32g474_conf.h"
#include <math.h>

#define SDP810_ADDR         0x25    /* I2C 7-bit, left-shifted = 0x4A */
#define FLOW_CALIB_K        0.0451f /* L/min per sqrt(Pa), calibrated restrictor */
#define BLOWER_PWM_HZ       25000u
#define BLOWER_PWM_TICKS    100u

static bool  enabled = false;
static float current_flow = 0.0f;
static float blower_duty = 0.0f;
static float integ = 0.0f;

static void i2c3_init(void)
{
    /* PA8 = I2C3_SCL, PA9 = I2C3_SDA */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->AFR[1] &= ~(GPIO_AFRH_AFSEL8 | GPIO_AFRH_AFSEL9);
    GPIOA->AFR[1] |= (8u << GPIO_AFRH_AFSEL8_Pos) | (8u << GPIO_AFRH_AFSEL9_Pos); /* AF8 = I2C3 */
    GPIOA->MODER = (GPIOA->MODER & ~(GPIO_MODER_MODE8 | GPIO_MODER_MODE9))
                 | (2u << GPIO_MODER_MODE8_Pos) | (2u << GPIO_MODER_MODE9_Pos);
    GPIOA->OTYPER |= GPIO_OTYPER_OT8 | GPIO_OTYPER_OT9;  /* open-drain */
    GPIOA->PUPDR = (GPIOA->PUPDR & ~(GPIO_PUPDR_PUPD8 | GPIO_PUPDR_PUPD9))
                 | (1u << GPIO_PUPDR_PUPD8_Pos) | (1u << GPIO_PUPDR_PUPD9_Pos);

    RCC->APB1ENR1 |= RCC_APB1ENR1_I2C3EN;
    I2C3->TIMINGR = 0x10900FAC;   /* 400 kHz @ 170 MHz */
    I2C3->CR1 = I2C_CR1_PE;
}

static int sdp810_read_dp(float *dp_pa)
{
    /* Trigger continuous read: write 0x361A to SDP810 */
    I2C3->CR2 = (SDP810_ADDR << 1) | (2u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    while (!(I2C3->ISR & I2C_ISR_TXIS)) {
        if (I2C3->ISR & I2C_ISR_NACKF) { I2C3->ICR = I2C_ICR_NACKCF; return -1; }
    }
    I2C3->TXDR = 0x36;
    while (!(I2C3->ISR & I2C_ISR_TXIS)) ;
    I2C3->TXDR = 0x1A;
    while (!(I2C3->ISR & I2C_ISR_TC)) ;
    I2C3->CR2 |= I2C_CR2_AUTOEND;

    /* Wait ~45 ms for conversion, then read 3 bytes */
    for (volatile int i = 0; i < 800000; ++i) ;   /* ~45 ms */

    I2C3->CR2 = (SDP810_ADDR << 1) | (3u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START | I2C_CR2_RD_WRN;
    uint8_t msb, crc, lsb;
    while (!(I2C3->ISR & I2C_ISR_RXNE)) ;
    msb = (uint8_t)I2C3->RXDR;
    while (!(I2C3->ISR & I2C_ISR_RXNE)) ;
    lsb = (uint8_t)I2C3->RXDR;
    while (!(I2C3->ISR & I2C_ISR_RXNE)) ;
    crc = (uint8_t)I2C3->RXDR;
    I2C3->CR2 |= I2C_CR2_AUTOEND;

    int16_t raw = (int16_t)((msb << 8) | lsb);
    *dp_pa = (float)raw / 60.0f;   /* SDP810: raw/60 = Pa */
    return 0;
}

void airflow_init(void)
{
    /* PB0 = TIM2_CH3 PWM for blower */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->AFR[0] &= ~GPIO_AFRL_AFSEL0;
    GPIOB->AFR[0] |= (1u << GPIO_AFRL_AFSEL0_Pos);  /* AF1 = TIM2_CH3 (alt: check datasheet) */
    GPIOB->MODER = (GPIOB->MODER & ~GPIO_MODER_MODE0) | (2u << GPIO_MODER_MODE0_Pos);

    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM2EN;
    TIM2->PSC = (SYSCLK_FREQ / BLOWER_PWM_HZ / BLOWER_PWM_TICKS) - 1;
    TIM2->ARR = BLOWER_PWM_TICKS - 1;
    TIM2->CCR3 = 0;
    TIM2->CCMR2 = TIM_CCMR2_OC3M_PWM1 | TIM_CCMR2_OC3PE;
    TIM2->CCER = TIM_CCER_CC3E;
    TIM2->BDTR |= TIM_BDTR_MOE;
    TIM2->CR1 = TIM_CR1_CEN;

    i2c3_init();
}

void airflow_start(void)
{
    enabled = true;
    blower_duty = 0.4f;
    integ = 0.0f;
    TIM2->CCR3 = (uint32_t)(blower_duty * BLOWER_PWM_TICKS);
}

void airflow_stop(void)
{
    enabled = false;
    blower_duty = 0.0f;
    TIM2->CCR3 = 0;
    current_flow = 0.0f;
}

float airflow_read_lpm(void)
{
    if (!enabled) return 0.0f;
    float dp;
    if (sdp810_read_dp(&dp) == 0) {
        /* Flow = K * sqrt(dP); dP can be negative (reverse) */
        if (dp < 0) dp = 0;
        current_flow = FLOW_CALIB_K * sqrtf(dp);
    }
    return current_flow;
}

bool airflow_ok(void)
{
    float f = airflow_read_lpm();
    return (f >= FLOW_MIN_LPM && f <= FLOW_MAX_LPM);
}

/* Called from main loop at ~10 Hz to run flow PI */
void airflow_loop(void)
{
    if (!enabled) { TIM2->CCR3 = 0; return; }
    float f = airflow_read_lpm();
    float err = FLOW_TARGET_LPM - f;
    integ += err * 0.05f;
    if (integ > 0.4f) integ = 0.4f;
    if (integ < 0.0f) integ = 0.0f;
    blower_duty = 0.35f + 0.15f * err + 0.3f * integ;
    if (blower_duty > 0.9f) blower_duty = 0.9f;
    if (blower_duty < 0.2f) blower_duty = 0.2f;
    TIM2->CCR3 = (uint32_t)(blower_duty * BLOWER_PWM_TICKS);
}