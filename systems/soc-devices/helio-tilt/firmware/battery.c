/*
 * battery.c — 18650 battery voltage monitor
 *
 * PA0 (ADC1_IN1) reads Vbat via 2:1 voltage divider.
 * 18650 range: 3.0V (empty) – 4.2V (full).
 */

#include "battery.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

void battery_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    RCC->AHB2ENR |= RCC_AHB12ENR_ADC12EN;   /* Enable ADC1/ADC2 clock */

    /* PA0 = analog input */
    GPIOA->MODER &= ~(3u << (0u * 2u));     /* Analog mode (00) */
    GPIOA->PUPDR &= ~(3u << (0u * 2u));     /* No pull */

    /* Configure ADC1: channel 1, 12-bit, software trigger */
    ADC1->CR = ADC_CR_ADVREGEN;             /* Enable voltage regulator */
    for (volatile int i = 0; i < 1000; i++) ;   /* Regulator startup */
    ADC1->CR |= ADC_CR_ADCAL;               /* Calibrate */
    while (ADC1->CR & ADC_CR_ADCAL) ;
    ADC1->CR |= ADC_CR_ADEN;                /* Enable ADC */
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) ;
}

float battery_read(void)
{
    /* Start conversion on channel 1 (PA0 = ADC1_IN1) */
    ADC1->SQR1 = (1u << 6);   /* 1 conversion, channel 1 */
    ADC1->CR |= ADC_CR_ADSTART;
    while (!(ADC1->ISR & ADC_ISR_EOC)) ;

    uint16_t raw = ADC1->DR;
    /* Convert: raw / 4095 × 3.3V × divider_ratio(2) = Vbat */
    float vbat = (float)raw / 4095.0f * 3.3f * BAT_DIVIDER_RATIO;
    return vbat;
}

int battery_low(void)
{
    float v = battery_read();
    return v < BAT_LOW_V ? 1 : 0;
}