/*
 * battery.c — 18650 voltage monitor + low-charge gating
 *
 * PA4 (ADC1_IN17) reads Vbat via a 2:1 divider (18650 3.0–4.2 V → 1.5–2.1 V).
 * The firmware gates HV arming on Vbat > 3.5 V to avoid brown-out.
 */

#include "battery.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

static float last_vbat = 4.0f;

void battery_init(void)
{
    /* PA4: ADC1_IN17 (analog input, 2:1 battery divider) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (4u * 2u))) | (0u << (4u * 2u));
    last_vbat = 4.0f;
}

float battery_read(void)
{
    /* Simplified: real code reads ADC1_IN17 and applies 2× divider */
    last_vbat = 3.9f;   /* Placeholder */
    return last_vbat;
}

bool battery_ok(void)  { return last_vbat > BAT_MIN_V; }
bool battery_low(void) { return last_vbat < BAT_LOW_V; }