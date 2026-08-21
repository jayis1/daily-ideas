/*
 * hv_supply.c — Cockcroft-Walton 30 kV HV supply control
 *
 * DAC1 (PA1) sets HV control voltage: 0–3.3 V → 0–30 kV (10 kV/V).
 * PA7 (HV_ENABLE) gates the MC34063A boost oscillator.
 * PB6 (active-low) controls bleeder FET (1 GΩ → GND).
 * ADC2 (PA3) monitors HV current: 100 Ω sense → AD8629 ×100 → 10 mV/µA.
 * ADC3 (PA5) monitors HV voltage: 10000:1 divider → 1 V/kV.
 *
 * Soft-start: ramp DAC1 from 0 to target over 5 s to avoid capillary
 * overheating from sudden electroosmotic flow.
 */

#include "hv_supply.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <math.h>

static float current_kv = 0.0f;
static float target_kv  = 0.0f;

void hv_supply_init(void)
{
    /* DAC1 on PA1 */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (1u * 2u))) | (0b11 << (1u * 2u));
    /* Enable DAC1 */
    RCC->APB1ENR1 |= RCC_APB1ENR1_DAC1EN;
    DAC1->MCR = DAC_MCR_MODE1_1;   /* Normal mode, output on PA1 */
    DAC1->CR |= DAC_CR_EN1;
    DAC1->DHR12R1 = 0;

    /* PA7: HV_ENABLE output */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (7u * 2u))) | (1u << (7u * 2u));
    GPIOA->BSRR = (1u << (7u + 16));  /* Low = off */

    /* PB6: bleeder (active-low FET) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (6u * 2u))) | (1u << (6u * 2u));
    GPIOB->BSRR = (1u << (6u + 16));  /* Low = bleeder ON (safe default) */

    /* PA3: ADC2 current monitor, PA5: ADC3 voltage monitor */
    GPIOA->MODER &= ~(3u << (3u * 2u));
    GPIOA->MODER &= ~(3u << (5u * 2u));

    current_kv = 0.0f;
    target_kv = 0.0f;
}

/* Set DAC1 output (0–4095 → 0–3.3 V) */
static void set_dac1(uint16_t val)
{
    if (val > 4095) val = 4095;
    DAC1->DHR12R1 = val;
}

/* Convert kV to DAC value: 30 kV → 3.3 V → 4095 */
static uint16_t kv_to_dac(float kv)
{
    float v = kv / HV_TARGET_KV_MAX * 3.3f;
    if (v < 0) v = 0;
    if (v > 3.3f) v = 3.3f;
    return (uint16_t)(v / 3.3f * 4095.0f);
}

void hv_supply_arm(bool en)
{
    if (en) {
        GPIOA->BSRR = (1u << 7);     /* PA7 high = enable */
        GPIOB->BSRR = (1u << 6);     /* PB6 high = bleeder OFF */
    } else {
        GPIOA->BSRR = (1u << (7 + 16));  /* PA7 low = disable */
        GPIOB->BSRR = (1u << (6 + 16));  /* PB6 low = bleeder ON */
    }
}

void hv_supply_ramp(float target, float ramp_time_s)
{
    target_kv = target;
    hv_supply_arm(true);

    /* Discharge bleeder, arm HV */
    GPIOB->BSRR = (1u << 6);     /* PB6 high = bleeder OFF */
    GPIOA->BSRR = (1u << 7);     /* PA7 high = enable */

    /* Ramp DAC1 from 0 to target over ramp_time_s */
    uint32_t steps = 200;  /* 200 steps = 25 ms each for 5 s ramp */
    float dac_step = (float)kv_to_dac(target) / (float)steps;
    for (uint32_t i = 0; i <= steps; i++) {
        set_dac1((uint16_t)(dac_step * (float)i));
        current_kv = target * (float)i / (float)steps;
        /* ~25 ms per step (simplified blocking delay) */
        for (volatile uint32_t j = 0; j < 100000; j++) ;
    }
    current_kv = target;
}

void hv_supply_off(void)
{
    set_dac1(0);
    GPIOA->BSRR = (1u << (7 + 16));  /* PA7 low = disable */
    current_kv = 0.0f;
    target_kv = 0.0f;
}

void hv_supply_discharge(void)
{
    set_dac1(0);
    GPIOA->BSRR = (1u << (7 + 16));  /* PA7 low = disable oscillator */
    GPIOB->BSRR = (1u << (6 + 16));  /* PB6 low = bleeder ON */
    /* Wait for discharge: τ = 1GΩ × ~100pF ≈ 100 ms → 5τ = 500 ms */
    for (volatile uint32_t i = 0; i < 5000000; i++) ;
    current_kv = 0.0f;
}

float hv_supply_read_voltage(void)
{
    /* ADC3 (PA5): 10000:1 divider. 30 kV → 3 V → 4095 counts.
     * kV = ADC * (3.0 / 4095) * HV_VMON_DIVIDER
     * Simplified: read ADC value (placeholder — real code configures ADC3)
     */
    uint16_t adc = 0;  /* Would read ADC3_DR */
    float v = (float)adc * (C4D_ADC_FULLSCALE / 4095.0f);
    return v * HV_VMON_DIVIDER / 1000.0f;  /* kV */
}

float hv_supply_read_current(void)
{
    /* ADC2 (PA3): 100 Ω sense × AD8629 ×100.
     * 1 µA HV current → 100 µV sense → 10 mV after ×100 → ADC counts.
     * µA = ADC * (3.0 / 4095) / (100 * 100e-6) * 1e6
     * Simplified placeholder:
     */
    uint16_t adc = 0;  /* Would read ADC2_DR */
    float v = (float)adc * (C4D_ADC_FULLSCALE / 4095.0f);
    /* v = I * R_sense * gain = I * 100 * 100 = I * 10000 (V per A) */
    return v * 1e6f / 10000.0f;  /* µA */
}