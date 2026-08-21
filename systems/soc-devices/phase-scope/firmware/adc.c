/*
 * Phase Scope — ADC driver
 * Dual ADC simultaneous sampling for voltage and current channels
 * DMA-based continuous acquisition with double buffering
 *
 * ADC1: V1, V2, V3 (voltage channels)
 * ADC2: I1, I2, I3 (current channels)
 * ADC3: NTC temp, VBAT (low-rate monitoring)
 */

#include "adc.h"
#include "main.h"
#include <string.h>

/* ------------------------------------------------------------------ */
/* Sample buffers (double-buffered DMA)                                */
/* ------------------------------------------------------------------ */

/* 1024 samples per channel, 6 channels, 2 buffers */
#define SAMPLES_PER_CHANNEL 1024
#define NUM_CHANNELS        6

ALIGN_32BYTES uint16_t adc_buffer_a[NUM_CHANNELS * SAMPLES_PER_CHANNEL];
ALIGN_32BYTES uint16_t adc_buffer_b[NUM_CHANNELS * SAMPLES_PER_CHANNEL];

volatile uint8_t  adc_buffer_ready = 0;  /* Set when half or full transfer */
volatile uint8_t  adc_active_buffer = 0; /* 0 = A, 1 = B */
volatile uint32_t adc_sample_index = 0;

/* Raw ADC readings for slow channels */
volatile uint16_t ntc_raw = 0;
volatile uint16_t vbat_raw = 0;

/* ------------------------------------------------------------------ */
/* ADC initialization                                                  */
/* ------------------------------------------------------------------ */

void adc_init(void)
{
    /* Enable ADC clocks */
    RCC->AHB2ENR |= RCC_AHB2ENR_ADC12EN | RCC_AHB2ENR_ADC345EN;
    RCC->AHB2ENR |= RCC_AHB2ENR_DMA1EN;

    /* Enable ADC voltage regulator */
    ADC1->CR &= ~ADC_CR_DEEPPWD;
    ADC1->CR |= ADC_CR_ADVREGEN;
    ADC2->CR &= ~ADC_CR_DEEPPWD;
    ADC2->CR |= ADC_CR_ADVREGEN;

    /* Wait for regulator startup */
    for (volatile int i = 0; i < 1000; i++)
        ;

    /* Calibrate ADCs */
    ADC1->CR &= ~ADC_CR_ADEN;
    ADC1->CR |= ADC_CR_ADCAL;
    while (ADC1->CR & ADC_CR_ADCAL)
        ;

    ADC2->CR &= ~ADC_CR_ADEN;
    ADC2->CR |= ADC_CR_ADCAL;
    while (ADC2->CR & ADC_CR_ADCAL)
        ;

    /* Configure ADC1: channels IN1, IN2, IN3 (PA0, PA1, PA2) */
    /* 12-bit resolution, right-aligned, oversampling disabled */
    ADC1->CFGR = ADC_CFGR_CONT                    /* Continuous mode */
               | ADC_CFGR_DMAEN                    /* DMA enabled */
               | ADC_CFGR_DMACFG                   /* Circular DMA */
               | (0x02 << ADC_CFGR_RES_Pos);       /* 12-bit */

    ADC1->SQR1 = (2 << ADC_SQR1_L_Pos)            /* 3 conversions */
               | (1 << ADC_SQR1_SQ1_Pos)           /* IN1 = V1 */
               | (2 << ADC_SQR1_SQ2_Pos)           /* IN2 = V2 */
               | (3 << ADC_SQR1_SQ3_Pos);          /* IN3 = V3 */

    /* Configure ADC2: channels IN4, IN5, IN6 (PA3, PA4, PA5) */
    ADC2->CFGR = ADC_CFGR_CONT
               | ADC_CFGR_DMAEN
               | ADC_CFGR_DMACFG
               | (0x02 << ADC_CFGR_RES_Pos);

    ADC2->SQR1 = (2 << ADC_SQR1_L_Pos)
               | (4 << ADC_SQR1_SQ1_Pos)           /* IN4 = I1 */
               | (5 << ADC_SQR1_SQ2_Pos)           /* IN5 = I2 */
               | (6 << ADC_SQR1_SQ3_Pos);          /* IN6 = I3 */

    /* Sampling time: 6.5 cycles for 50/60 Hz signals — actually use 24.5
     * for better accuracy with high-impedance sources */
    ADC1->SMPR1 = (0x04 << ADC_SMPR1_SMP1_Pos)
                | (0x04 << ADC_SMPR1_SMP2_Pos)
                | (0x04 << ADC_SMPR1_SMP3_Pos);    /* 24.5 cycles */

    ADC2->SMPR1 = (0x04 << ADC_SMPR1_SMP4_Pos)
                | (0x04 << ADC_SMPR1_SMP5_Pos)
                | (0x04 << ADC_SMPR1_SMP6_Pos);

    /* Configure dual ADC mode: simultaneous */
    ADC12_COMMON->CCR = (0x01 << ADC12_CCR_DUAL_Pos) /* Regular simultaneous */
                      | ADC12_CCR_MDMA;               /* DMA at end of each conv */

    /* Enable ADCs */
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY))
        ;
    ADC2->CR |= ADC_CR_ADEN;
    while (!(ADC2->ISR & ADC_ISR_ADRDY))
        ;

    /* Configure DMA1 Channel 1 for ADC1 (voltage) */
    DMA1_Channel1->CPAR = (uint32_t)&ADC12_COMMON->CDR; /* Dual mode CDR */
    DMA1_Channel1->CMAR = (uint32_t)adc_buffer_a;
    DMA1_Channel1->CNDTR = NUM_CHANNELS * SAMPLES_PER_CHANNEL;
    DMA1_Channel1->CCR = DMA_CCR_MINC      /* Memory increment */
                       | DMA_CCR_CIRC       /* Circular mode */
                       | DMA_CCR_PL(0x03)   /* Very high priority */
                       | DMA_CCR_MSIZE_1    /* 32-bit memory */
                       | DMA_CCR_PSIZE_1    /* 32-bit peripheral */
                       | DMA_CCR_HTIE      /* Half-transfer interrupt */
                       | DMA_CCR_TCIE;     /* Transfer-complete interrupt */

    NVIC_SetPriority(DMA1_Channel1_IRQn, 1);
    NVIC_EnableIRQ(DMA1_Channel1_IRQn);

    DMA1_Channel1->CCR |= DMA_CCR_EN;

    /* Start ADC conversions */
    ADC1->CR |= ADC_CR_ADSTART;
    ADC2->CR |= ADC_CR_ADSTART;
}

/* ------------------------------------------------------------------ */
/* DMA interrupt — double-buffer swap                                  */
/* ------------------------------------------------------------------ */

void DMA1_Channel1_IRQHandler(void)
{
    uint32_t isr = DMA1->ISR;

    if (isr & DMA_ISR_HTIF1) {
        /* Half-transfer: first half of buffer A is ready */
        DMA1->IFCR = DMA_ICR_HTIF1;
        adc_active_buffer = 0;
        adc_sample_index = 0;
        adc_buffer_ready = 1;
    }

    if (isr & DMA_ISR_TCIF1) {
        /* Transfer complete: second half of buffer A is ready */
        DMA1->IFCR = DMA_ICR_TCIF1;
        adc_active_buffer = 1;
        adc_sample_index = SAMPLES_PER_CHANNEL;
        adc_buffer_ready = 1;
    }
}

/* ------------------------------------------------------------------ */
/* Get pointer to sample buffer                                        */
/* ------------------------------------------------------------------ */

uint16_t *adc_get_buffer(uint8_t *which)
{
    if (which)
        *which = adc_active_buffer;

    return (adc_active_buffer == 0) ? adc_buffer_a : adc_buffer_b;
}

/* ------------------------------------------------------------------ */
/* Read slow ADC channels (NTC, VBAT)                                  */
/* ------------------------------------------------------------------ */

void adc_read_slow_channels(void)
{
    /* ADC3 for NTC (PB0 = IN12) and VBAT (PB1 = IN13) */
    /* Single conversion, polling mode */
    ADC3_COMMON->CCR = 0;

    /* Enable ADC3 */
    RCC->AHB2ENR |= RCC_AHB2ENR_ADC345EN;
    ADC3->CR &= ~ADC_CR_DEEPPWD;
    ADC3->CR |= ADC_CR_ADVREGEN;
    for (volatile int i = 0; i < 1000; i++)
        ;

    ADC3->CR &= ~ADC_CR_ADEN;
    ADC3->CR |= ADC_CR_ADCAL;
    while (ADC3->CR & ADC_CR_ADCAL)
        ;

    ADC3->CFGR = (0x02 << ADC_CFGR_RES_Pos); /* 12-bit */
    ADC3->SMPR1 = (0x06 << ADC_SMPR1_SMP12_Pos)  /* 247.5 cycles for NTC */
                | (0x06 << ADC_SMPR1_SMP13_Pos);

    ADC3->CR |= ADC_CR_ADEN;
    while (!(ADC3->ISR & ADC_ISR_ADRDY))
        ;

    /* Read NTC */
    ADC3->SQR1 = (0 << ADC_SQR1_L_Pos) | (12 << ADC_SQR1_SQ1_Pos);
    ADC3->CR |= ADC_CR_ADSTART;
    while (!(ADC3->ISR & ADC_ISR_EOC))
        ;
    ntc_raw = ADC3->DR;

    /* Read VBAT */
    ADC3->SQR1 = (0 << ADC_SQR1_L_Pos) | (13 << ADC_SQR1_SQ1_Pos);
    ADC3->CR |= ADC_CR_ADSTART;
    while (!(ADC3->ISR & ADC_ISR_EOC))
        ;
    vbat_raw = ADC3->DR;

    ADC3->CR |= ADC_CR_ADDIS;
}