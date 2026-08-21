/*
 * safety.c — Over-temperature safety watchdog
 *
 * Three independent safety layers:
 * 1. Software watchdog (IWDG) — resets MCU if loop stalls
 * 2. Hardware comparator (TLV3201) — cuts heater gate at 320°C
 * 3. One-shot thermal fuse — blows at 250°C (passive, permanent)
 *
 * This module handles layer 1 (software) and monitors layer 2
 * (comparator output on PB8 via EXTI).
 */

#include "stm32g491_conf.h"
#include "safety.h"
#include "heater.h"

static volatile bool overtemp_triggered = false;

void safety_init(void) {
    /* Enable IWDG (independent watchdog) */
    /* Timeout = (RLR+1) × (PR+4) / 32000 ≈ 1.04 s with RLR=4095, PR=0 */
    IWDG_KR = 0xCCCC;  /* enable IWDG */
    IWDG_PR = 0x00;     /* prescaler = /4 */
    IWDG_RLR = 0xFFF;   /* reload = 4095 */
    while (IWDG_SR & 0x01) ;  /* wait for PVU to clear */

    /* PB8: safety comparator output, input with pull-up */
    GPIO_MODER(GPIOB_BASE) &= ~(3U << (8*2));
    GPIO_PUPDR(GPIOB_BASE) |= (1U << (8*2));

    /* EXTI8: falling edge triggers interrupt (comparator output goes LOW on overtemp) */
    EXTI_IMR1 |= (1U << 8);    /* unmask EXTI8 */
    EXTI_FTSR1 |= (1U << 8);   /* falling edge */

    /* Enable EXTI9_5 IRQ (line 5..9 go through IRQ 23) */
    NVIC_ISER0 |= (1U << 23);

    overtemp_triggered = false;
}

void safety_kick(void) {
    IWDG_KR = 0xAAAA;  /* reload the watchdog */
}

bool safety_check(float pan_temp) {
    safety_kick();  /* refresh watchdog every cycle */

    /* Software over-temperature check */
    if (pan_temp > TEMP_SAFETY_C) {
        safety_emergency_cutoff();
        return true;
    }

    /* Check hardware comparator output */
    if (!(GPIO_IDR(SAFETY_CMP_PORT) & (1U << SAFETY_CMP_PIN))) {
        /* Comparator output LOW = overtemp condition */
        if (!overtemp_triggered) safety_emergency_cutoff();
        return true;
    }

    return false;
}

void safety_emergency_cutoff(void) {
    /* Immediately disable heaters */
    heater_off();
    GPIO_CLR(HEATER_EN_PORT, HEATER_EN_PIN);
    /* Clear PWM */
    TIM1_CCR1 = 0;
    TIM1_CCR2 = 0;
    overtemp_triggered = true;
}

bool safety_is_overtemp(void) {
    return overtemp_triggered;
}

void safety_clear(void) {
    overtemp_triggered = false;
}

/* EXTI9_5 handler — safety comparator interrupt */
void EXTI9_5_IRQHandler(void) {
    if (EXTI_PR1 & (1U << 8)) {
        EXTI_PR1 = (1U << 8);  /* clear pending */
        safety_emergency_cutoff();
    }
}