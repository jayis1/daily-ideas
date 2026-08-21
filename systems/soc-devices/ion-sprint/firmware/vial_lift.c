/*
 * vial_lift.c — NEMA8 stepper motor for hydrodynamic injection
 *
 * TIM2_CH1 (PA8) generates step pulses for the NEMA8 stepper via DRV8833.
 * PC0 sets direction, PC1 enables the driver (active-low).
 * PC5 reads the home limit switch.
 * 200 steps/rev, M3 lead screw (0.5 mm/rev) → 0.0025 mm/step.
 * Lift 100 mm = 40000 steps at 400 steps/s → 100 s.
 */

#include "vial_lift.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

void vial_lift_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOCEN;

    /* PA8: TIM1_CH1 step pulse output (using TIM1 for higher speed) */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (8u * 2u))) | (2u << (8u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 0)) | (6u << 0);  /* AF6 = TIM1 */

    /* PC0: direction */
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (0u * 2u))) | (1u << (0u * 2u));
    /* PC1: enable (active-low) */
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (1u * 2u))) | (1u << (1u * 2u));
    GPIOC->BSRR = (1u << (1 + 16));  /* Disabled (high) */
    /* PC5: home limit switch (input, pull-up) */
    GPIOC->MODER &= ~(3u << (5u * 2u));
    GPIOC->PUPDR = (GPIOC->PUPDR & ~(3u << (5u * 2u))) | (1u << (5u * 2u));

    /* TIM1: step pulse generator */
    RCC->APB2ENR |= RCC_APB2ENR_TIM1EN;
    TIM1->PSC = (SYSCLK_FREQ / LIFT_SPEED_SPS) - 1;  /* Steps per second */
    TIM1->ARR = 1;  /* 1 pulse per period */
    TIM1->CCR1 = 1;
    TIM1->CCMR1 = TIM_CCMR1_OC1M_1 | TIM_CCMR1_OC1M_2;
    TIM1->CCER = TIM_CCER_CC1E;
    TIM1->BDTR = TIM_BDTR_MOE;  /* Advanced timer: enable output */
}

static void step_pulse(uint32_t count)
{
    GPIOC->BSRR = (1u << 1);  /* Enable (low) */
    for (uint32_t i = 0; i < count; i++) {
        GPIOA->BSRR = (1u << 8);    /* Pulse high */
        for (volatile int j = 0; j < 100; j++) ;
        GPIOA->BSRR = (1u << (8 + 16));  /* Pulse low */
        for (volatile int j = 0; j < 100; j++) ;
    }
    GPIOC->BSRR = (1u << (1 + 16));  /* Disable (high) */
}

void vial_lift_up(float lift_mm)
{
    uint32_t steps = (uint32_t)(lift_mm * STEPS_PER_MM);
    GPIOC->BSRR = (1u << 0);     /* Direction: up */
    step_pulse(steps);
}

void vial_lift_down(float lift_mm)
{
    uint32_t steps = (uint32_t)(lift_mm * STEPS_PER_MM);
    GPIOC->BSRR = (1u << (0 + 16));  /* Direction: down */
    step_pulse(steps);
}

void vial_lift_home(void)
{
    GPIOC->BSRR = (1u << (0 + 16));  /* Direction: down */
    GPIOC->BSRR = (1u << 1);         /* Enable */
    /* Step until home switch triggers */
    while (GPIOC->IDR & (1u << 5)) {  /* While not at home (high = not home) */
        GPIOA->BSRR = (1u << 8);
        for (volatile int j = 0; j < 100; j++) ;
        GPIOA->BSRR = (1u << (8 + 16));
        for (volatile int j = 0; j < 100; j++) ;
    }
    GPIOC->BSRR = (1u << (1 + 16));  /* Disable */
}