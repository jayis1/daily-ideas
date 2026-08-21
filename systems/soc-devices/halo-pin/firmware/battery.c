/*
 * battery.c — 18650 voltage monitor via ADC2_IN4 (PA4)
 *
 * 2:1 divider on Vbat → PA4 (ADC2 channel 4)
 */

#include "battery.h"
#include "stm32g474_conf.h"

static float vbat = 4.0f;

void battery_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_ADC12EN;
    GPIOA->MODER &= ~GPIO_MODER_MODE4;   /* PA4 analog */
    ADC2->CR |= ADC_CR_ADVREGEN;
    for (volatile int i = 0; i < 10000; ++i) ;
    ADC2->CR &= ~ADC_CR_DEEPPWD;
    ADC2->CR |= ADC_CR_ADCAL;
    while (ADC2->CR & ADC_CR_ADCAL) ;
    ADC2->CR |= ADC_CR_ADEN;
    while (!(ADC2->ISR & ADC_ISR_ADRDY)) ;
}

float battery_read(void)
{
    ADC2->SQR1 = (1u << 6) | (4u << 9);   /* 1 conversion, ch4 */
    ADC2->CR |= ADC_CR_ADSTART;
    while (!(ADC2->ISR & ADC_ISR_EOC)) ;
    uint16_t raw = (uint16_t)ADC2->DR;
    vbat = (float)raw / 4095.0f * 3.3f * 2.0f;   /* 2:1 divider */
    return vbat;
}

bool battery_ok(void)  { return battery_read() > 3.4f; }
bool battery_low(void) { return battery_read() < 3.4f; }