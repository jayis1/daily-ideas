/*
 * pump.c — Peristaltic pump for capillary flushing
 *
 * TIM4_CH1 (PB8) generates PWM for the peristaltic pump DC motor via
 * DRV8833 H-bridge. PB9 sets direction (forward = flush).
 */

#include "pump.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

void pump_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    /* PB8: TIM4_CH1 PWM output */
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (8u * 2u))) | (2u << (8u * 2u));
    GPIOB->AFR[1] = (GPIOB->AFR[1] & ~(0xFu << 0)) | (2u << 0);  /* AF2 = TIM4 */
    /* PB9: direction output */
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (9u * 2u))) | (1u << (9u * 2u));
    GPIOB->BSRR = (1u << 9);  /* Forward */

    /* TIM4: PWM mode, 1 kHz */
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM4EN;
    TIM4->PSC = (SYSCLK_FREQ / 1000000u) - 1;  /* 1 MHz tick */
    TIM4->ARR = 1000 - 1;  /* 1 kHz PWM */
    TIM4->CCR1 = 0;
    TIM4->CCMR1 = TIM_CCMR1_OC1M_1 | TIM_CCMR1_OC1M_2;  /* PWM mode 1 */
    TIM4->CCER = TIM_CCER_CC1E;
    TIM4->CR1 = TIM_CR1_CEN;
}

void pump_flush(uint32_t flush_time_s)
{
    GPIOB->BSRR = (1u << 9);  /* Forward direction */
    TIM4->CCR1 = (1000u * PUMP_DUTY_FLUSH) / 100u;  /* Set duty */

    /* Blocking wait for flush_time_s (simplified) */
    for (volatile uint32_t i = 0; i < flush_time_s * 100000u; i++) ;
}

void pump_off(void)
{
    TIM4->CCR1 = 0;
}