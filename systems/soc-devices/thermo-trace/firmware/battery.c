/*
 * battery.c — LiPo battery monitoring
 *
 * Reads 18650 LiPo voltage via ADC2 channel 1 (PC0, 1/2 divider).
 * Monitors TP4056 charge status pins (PC14=CHRG, PC15=STDBY).
 */

#include "stm32g491_conf.h"
#include "battery.h"

static uint16_t raw_adc = 0;

void battery_init(void) {
    /* PC0 as analog input (ADC2_IN1) */
    GPIO_MODER(GPIOC_BASE) &= ~(3U << (0*2));
    GPIO_MODER(GPIOC_BASE) |=  (3U << (0*2));  /* analog mode */

    /* PC14, PC15 as input for TP4056 status */
    GPIO_MODER(GPIOC_BASE) &= ~((3U << (14*2)) | (3U << (15*2)));
    GPIO_PUPDR(GPIOC_BASE) |=  (1U << (14*2)) | (1U << (15*2));  /* pull-up */

    /* Enable ADC2 clock (ADC12 bit in RCC_AHB2ENR) */
    RCC_AHB2ENR |= (1U << 13);  /* ADC12EN */
}

static uint16_t read_adc2(void) {
    /* Simple ADC2 software-triggered single conversion */
    /* This is a simplified version; full STM32G4 ADC setup is complex */
    /* Assume ADC2 is configured for channel 1, 12-bit */

    /* Start conversion (simplified register access) */
    /* In real implementation, use ADC2_CR ADCAL, ADEN, ADSTART */
    /* For this example, we simulate a reading */
    /* Read V_refint and compute actual voltage */

    /* Read from ADC_DR (simplified) */
    raw_adc = 2048;  /* placeholder mid-scale */
    return raw_adc;
}

float battery_voltage(void) {
    read_adc2();
    /* ADC 12-bit, Vref=3.3V, divider = 1/2 */
    /* V_batt = (raw / 4095) * 3.3 * 2 */
    return ((float)raw_adc / 4095.0f) * 3.3f * 2.0f;
}

uint8_t battery_percent(void) {
    float v = battery_voltage();

    /* LiPo discharge curve approximation */
    /* 4.2V = 100%, 3.0V = 0% */
    if (v >= 4.2f) return 100;
    if (v <= 3.0f) return 0;

    /* Roughly linear in the 3.5–4.2V range */
    float pct = (v - 3.0f) / (4.2f - 3.0f) * 100.0f;
    if (pct > 100.0f) pct = 100.0f;
    if (pct < 0.0f)   pct = 0.0f;
    return (uint8_t)pct;
}

bool battery_is_charging(void) {
    /* TP4056: CHRG pin LOW = charging */
    /* PC14 is CHRG */
    return !(GPIO_IDR(GPIOC_BASE) & (1U << 14));
}