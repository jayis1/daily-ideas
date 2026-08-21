/*
 * filter_wheel.c — 6-position filter wheel (SG90 servo)
 *
 * TIM4_CH1 (PB8) generates 50 Hz PWM.
 * Pulse width: 1.0 ms = position 0, +0.2 ms per position, 2.0 ms = position 5.
 * Optical slot sensor on PC10 detects the home position.
 */

#include "filter_wheel.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

static uint8_t current_pos = 0;

void filter_wheel_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN | RCC_AHB2ENR_GPIOCEN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_TIM4EN;

    /* PB8 = TIM4_CH3 (AF2) — actually TIM4_CH3 on PB8 */
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (8u * 2u))) | (2u << (8u * 2u));
    GPIOB->AFR[1] = (GPIOB->AFR[1] & ~(0xFu << 0)) | (2u << 0);  /* AF2 */

    /* PC10 = input (filter wheel home sensor) */
    GPIOC->MODER &= ~(3u << (10u * 2u));
    GPIOC->PUPDR |=  (2u << (10u * 2u));   /* Pull-down */

    /* TIM4: 50 Hz PWM
     * APB1 timer clock = 170 MHz / 2 × 2 = 170 MHz (when APB1 prescaler != 1)
     * Prescaler = 1700 → timer clock = 100 kHz
     * ARR = 2000 → 50 Hz (20 ms period)
     * Pulse 1.0–2.0 ms → CCR = 100–200
     */
    TIM4->PSC = 1700 - 1;
    TIM4->ARR = 2000 - 1;
    TIM4->CCR3 = SERVO_PULSE_MIN_US / 10;   /* 1.0 ms → 100 counts */
    TIM4->CCMR2 = (6u << TIM_CCMR2_OC3M_Pos) | TIM_CCMR2_OC3PE;  /* PWM mode 1 */
    TIM4->CCER = TIM_CCER_CC3E;
    TIM4->CR1 = TIM_CR1_CEN;

    current_pos = 0;
}

void filter_wheel_set(uint8_t position)
{
    if (position >= FILTER_WHEEL_COUNT) return;
    uint16_t pulse_us = SERVO_PULSE_MIN_US
                      + position * SERVO_PULSE_STEP_US;
    TIM4->CCR3 = pulse_us / 10;   /* 100 kHz timer → 1 count = 10 µs */
    current_pos = position;
}

uint8_t filter_wheel_get(void)
{
    return current_pos;
}

int filter_wheel_home(void)
{
    /* Rotate servo slowly until the optical slot sensor on PC10 triggers */
    for (uint8_t pos = 0; pos < FILTER_WHEEL_COUNT; pos++) {
        filter_wheel_set(pos);
        /* Wait for servo to settle (~300 ms) */
        for (volatile uint32_t i = 0; i < 5000000; i++) ;
        /* Check home sensor */
        if (GPIOC->IDR & (1u << 10)) {
            current_pos = 0;   /* Home position = 405 nm */
            return 0;
        }
    }
    return -1;   /* Home not found */
}