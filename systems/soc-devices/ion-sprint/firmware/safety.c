/*
 * safety.c — HV safety monitoring
 *
 * Multiple safety layers:
 * 1. Hardware: TLV3201 comparator trips at 250 µA, gates off CW oscillator.
 * 2. Firmware: monitors ADC2 (current) and ADC3 (voltage), aborts if
 *    current > 200 µA or voltage deviates >±2 kV from setpoint.
 * 3. Interlock: PB7 reads lid switch, refuses to arm if open.
 * 4. Bleeder: PB6 (active-low) connects 1 GΩ to GND when HV is off.
 */

#include "safety.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

void safety_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN | RCC_AHB2ENR_GPIOCEN;
    /* PB7: interlock switch (input, pull-up) */
    GPIOB->MODER &= ~(3u << (7u * 2u));
    GPIOB->PUPDR = (GPIOB->PUPDR & ~(3u << (7u * 2u))) | (1u << (7u * 2u));
    /* PC3: TLV3201 fault output (input) */
    GPIOC->MODER &= ~(3u << (3u * 2u));
    GPIOC->PUPDR = (GPIOC->PUPDR & ~(3u << (3u * 2u))) | (1u << (3u * 2u));
    /* PC2: HV cutoff gate (output) */
    GPIOC->MODER = (GPIOC->MODER & ~(3u << (2u * 2u))) | (1u << (2u * 2u));
    GPIOC->BSRR = (1u << 2);   /* High = allow HV (gate not tripped) */
}

bool safety_check(float current_ua, float voltage_kv)
{
    /* Check current limit (firmware backup to HW comparator) */
    if (current_ua > HV_CURRENT_MAX_UA) return true;

    /* Check HW comparator trip */
    if (safety_hw_trip()) return true;

    /* Check voltage deviation (if we know the setpoint) */
    /* The caller (main.c) checks voltage vs setpoint separately */
    if (voltage_kv < 0.0f || voltage_kv > HV_TARGET_KV_MAX) return true;

    return false;
}

bool safety_interlock_ok(void)
{
    /* PB7 high = lid closed (pull-up), low = open */
    return (GPIOB->IDR & (1u << 7)) != 0;
}

bool safety_hw_trip(void)
{
    /* PC3 high = TLV3201 output not tripped (pulled up),
     * low = tripped (open-drain comparator pulled low) */
    return (GPIOC->IDR & (1u << 3)) == 0;
}