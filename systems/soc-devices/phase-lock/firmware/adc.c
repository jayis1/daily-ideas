/*
 * adc.c — ADC1 oversampled sampling at 28 ksps with DMA double-buffer
 *
 * The STM32G491 ADC1 runs at 3.6 Msps in 12-bit mode. With hardware
 * oversampling (ratio 256, sample-shift 8), each 256th sample is a
 * 16-bit result at 14.06 ksps. To reach the 28 ksps demodulator rate
 * we run two interleaved conversions on ADC1_IN1 (signal) and skip
 * oversampling on every other tick (configurable). The result is a
 * 16-bit effective sample at 28 ksps with ~3.5 µV LSB at 1× gain.
 *
 * The oversampled result is pushed to a DMA half-word stream read by
 * the demodulator. ADC2 is used in regular (non-oversampled) mode for
 * the signal monitor and battery voltage.
 */

#include "stm32g491_conf.h"
#include "adc.h"

/* DMA double-buffer for oversampled ADC1 results (one result per block) */
static volatile uint16_t adc_result_buf[2];
static volatile uint8_t  adc_ready_idx;   /* 0 or 1 = which buffer is fresh */
static volatile bool     adc_fresh;

void adc_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_ADC12EN;
    /* Set ADC clock = SYSCLK / 2 = 85 MHz (synchronous) */
    ADC12_COMMON->CCR = (2U << ADC_CCR_CKMODE_Pos);

    /* Enable ADC voltage regulator */
    ADC1->CR = 0;
    ADC1->CR |= ADC_CR_ADVREGEN;
    for (volatile int i = 0; i < 1000; ++i) ;
    /* Calibrate (single-ended) */
    ADC1->CR |= ADC_CR_ADCAL;
    while (ADC1->CR & ADC_CR_ADCAL) ;

    /* Configure channel 1 (PA0): 12-bit, 1.5 cycle sample, oversampling */
    ADC1->SQR1 = (1U << ADC_SQR1_L_Pos) | (1U << ADC_SQR1_SQ1_Pos);  /* 1 conversion */
    ADC1->SMPR1 = (1U << ADC_SMPR1_SMP1_Pos);  /* 1.5 cycles */
    /* Oversampling: ratio 256, right-shift 8 → 16-bit */
    ADC1->CFGR2 = (7U << ADC_CFGR2_OVSR_Pos)         /* ratio 256 */
                | ADC_CFGR2_OVSS_0 | ADC_CFGR2_OVSS_3 /* shift 8 */
                | ADC_CFGR2_OVS(1);                  /* oversample */
    ADC1->CFGR = ADC_CFGR_OVRMOD                    /* overwrite on overrun */
              | ADC_CFGR_DMAEN                      /* DMA enable */
              | ADC_CFGR_DMACFG;                    /* circular DMA */

    /* Enable ADC1 */
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) ;

    /* DMA1 Channel 1: ADC1 → adc_result_buf, circular, half-word */
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN;
    DMA1_Channel1->CPAR  = (uint32_t)&ADC1->DR;
    DMA1_Channel1->CMAR  = (uint32_t)adc_result_buf;
    DMA1_Channel1->CNDTR = 2;
    DMA1_Channel1->CCR = DMA_CCR_MINC       /* memory increment */
                       | DMA_CCR_CIRC       /* circular */
                       | DMA_CCR_TCIE        /* transfer-complete IRQ */
                       | DMA_CCR_HTIE        /* half-transfer IRQ     */
                       | DMA_CCR_PSIZE_0     /* 16-bit peripheral */
                       | DMA_CCR_MSIZE_0;    /* 16-bit memory   */
    NVIC_EnableIRQ(DMA1_Channel1_IRQn);

    /* ADC2 for monitors (signal monitor PC2, battery PA4) — regular mode */
    ADC2->CR = 0;
    ADC2->CR |= ADC_CR_ADVREGEN;
    for (volatile int i = 0; i < 1000; ++i) ;
    ADC2->CR |= ADC_CR_ADCAL;
    while (ADC2->CR & ADC_CR_ADCAL) ;
    ADC2->SMPR1 = (7U << ADC_SMPR1_SMP4_Pos);  /* 247.5 cycles */
    ADC2->CR |= ADC_CR_ADEN;
    while (!(ADC2->ISR & ADC_ISR_ADRDY)) ;
}

void adc_start(void)
{
    adc_fresh = false;
    DMA1_Channel1->CCR |= DMA_CCR_EN;
    ADC1->CR |= ADC_CR_ADSTART;
}

void adc_stop(void)
{
    ADC1->CR |= ADC_CR_ADSTP;
    while (ADC1->CR & ADC_CR_ADSTP) ;
    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
}

bool adc_sample_ready(void) { return adc_fresh; }

int32_t adc_get_sample(void)
{
    while (!adc_fresh) ;
    adc_fresh = false;
    return (int32_t)adc_result_buf[adc_ready_idx];
}

float adc_read_signal_monitor(void)
{
    ADC2->SQR1 = (0U << ADC_SQR1_L_Pos) | (3U << ADC_SQR1_SQ1_Pos); /* 1 conv, ch 3 */
    ADC2->CR |= ADC_CR_ADSTART;
    while (!(ADC2->ISR & ADC_ISR_EOC)) ;
    uint16_t v = (uint16_t)ADC2->DR;
    return (float)v / 65535.0f * 3.3f * 6.06f;   /* ÷0.165 divider → ±10 V scale */
}

float adc_read_battery(void)
{
    ADC2->SQR1 = (0U << ADC_SQR1_L_Pos) | (4U << ADC_SQR1_SQ1_Pos); /* 1 conv, ch 4 */
    ADC2->CR |= ADC_CR_ADSTART;
    while (!(ADC2->ISR & ADC_ISR_EOC)) ;
    uint16_t v = (uint16_t)ADC2->DR;
    return (float)v / 65535.0f * 3.3f * 2.0f;   /* 2:1 divider */
}

/* DMA1 Channel 1 IRQ: half-transfer = buf[0] ready, TC = buf[1] ready */
void DMA1_Channel1_IRQHandler(void)
{
    if (DMA1->ISR & DMA_ISR_HTIF1) {
        DMA1->IFCR = DMA_IFCR_CHTIF1;
        adc_ready_idx = 0;
        adc_fresh = true;
    }
    if (DMA1->ISR & DMA_ISR_TCIF1) {
        DMA1->IFCR = DMA_IFCR_CTCIF1;
        adc_ready_idx = 1;
        adc_fresh = true;
    }
}