/*
 * adc.c — STM32G474 ADC1: 3.6 Msps ToF capture + 28 ksps BUA oversample
 *
 * ADC1 (PA0, ADC1_IN1) is the RX signal input.
 *
 * ToF mode:
 *   - Full 3.6 Msps, 12-bit, DMA into a 115200-sample buffer.
 *   - Hardware trigger from HRTIM_CHA1 (TX trigger edge).
 *   - 32 ms window captures the full A-scan (TX burst + propagation + echoes).
 *
 * BUA mode:
 *   - Hardware oversampling ×256 with sample-shift 8 → 16-bit @ 28 ksps.
 *   - 50 ms window → 1400 samples (after digital I/Q demod at 1 MHz).
 *   - DMA into a 1400-sample buffer.
 *
 * Buffers are in a dedicated SRAM2 region to avoid DMA contention.
 */

#include "adc.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

/* DMA buffers — placed in SRAM1 (128 KB SRAM, both regions accessible) */
static uint16_t tof_buf[TOF_SAMPLES]   __attribute__((section(".bss")));
static uint16_t bua_buf[BUA_SAMPLES]   __attribute__((section(".bss")));

static volatile bool tof_done = false;
static volatile bool bua_done = false;

void adc_init(void)
{
    /* PA0: ADC1_IN1 (analog input) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (0u * 2u))) | (0u << (0u * 2u)); /* Analog */
    GPIOA->PUPDR &= ~(3u << (0u * 2u));   /* No pull */

    /* Enable ADC1 clock */
    RCC->AHB2ENR |= RCC_AHB2ENR_ADC12EN;

    /* ADC common configuration */
    ADC12_COMMON->CCR = 0;   /* No common config needed */

    /* ADC1 configuration */
    ADC1->CR = 0;
    ADC1->CR |= ADC_CR_ADVREGEN;   /* Enable voltage regulator */
    for (volatile int i = 0; i < 100; ++i) ;   /* Wait for regulator */
    ADC1->CR |= ADC_CR_ADCAL;       /* Self-calibration */
    while (ADC1->CR & ADC_CR_ADCAL) ;

    /* Configure channel 1 (PA0), 12-bit, single-ended */
    ADC1->SQR1 = (1u << 6);   /* 1 conversion: channel 1 */
    ADC1->SMPR1 = 0;          /* Minimum sample time (for 3.6 Msps) */
    ADC1->CFGR = 0;           /* Default config, DMA mode 1, 12-bit */

    /* Enable DMA for ADC1 */
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN;
    DMA1_Channel1->CPAR = (uint32_t)&ADC1->DR;
    DMA1_Channel1->CMAR = (uint32_t)tof_buf;
    DMA1_Channel1->CNDTR = TOF_SAMPLES;

    tof_done = bua_done = false;
}

void adc_start_tof_capture(void)
{
    /* Full 3.6 Msps mode: 12-bit, no oversampling, DMA 115200 samples */
    ADC1->CFGR = ADC_CFGR_DMAEN | ADC_CFGR_DMACFG | (0u << ADC_CFGR_OVSR_Pos)
               | ADC_CFGR_OVRMOD;
    /* Disable oversampling for full rate */
    ADC1->CFGR2 = 0;

    DMA1_Channel1->CMAR = (uint32_t)tof_buf;
    DMA1_Channel1->CNDTR = TOF_SAMPLES;
    DMA1_Channel1->CCR = DMA_CCR_EN | DMA_CCR_MINC | DMA_CCR_TCIE
                        | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_0;
    DMA1_Channel1->CPAR = (uint32_t)&ADC1->DR;

    /* Hardware trigger: HRTIM_CHA1 (TX trigger) */
    ADC1->CFGR |= (3u << ADC_CFGR_EXTSEL_Pos) | ADC_CFGR_EXTEN_0;   /* HRTIM trigger */

    tof_done = false;
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) ;
    ADC1->CR |= ADC_CR_ADSTART;
}

void adc_wait_tof_done(void)
{
    while (!tof_done) ;
    ADC1->CR |= ADC_CR_ADSTP;
    while (ADC1->CR & ADC_CR_ADSTART) ;
}

void adc_start_bua_capture(void)
{
    /* Oversampled 16-bit @ 28 ksps: oversampling ratio 256, right-shift 8 */
    ADC1->CFGR = ADC_CFGR_DMAEN | ADC_CFGR_DMACFG | ADC_CFGR_OVRMOD;
    ADC1->CFGR2 = (256u << ADC_CFGR2_OVSR_Pos) | (8u << ADC_CFGR2_OVSS_Pos)
                | ADC_CFGR2_ROVSE;

    DMA1_Channel1->CMAR = (uint32_t)bua_buf;
    DMA1_Channel1->CNDTR = BUA_SAMPLES;
    DMA1_Channel1->CCR = DMA_CCR_EN | DMA_CCR_MINC | DMA_CCR_TCIE
                        | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_1;   /* 16-bit dest */

    /* Software trigger for BUA (no HRTIM trigger) */
    ADC1->CFGR &= ~ADC_CFGR_EXTEN;

    bua_done = false;
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) ;
    ADC1->CR |= ADC_CR_ADSTART;
}

void adc_wait_bua_done(void)
{
    while (!bua_done) ;
    ADC1->CR |= ADC_CR_ADSTP;
    while (ADC1->CR & ADC_CR_ADSTART) ;
}

const uint16_t* adc_tof_buffer(void) { return tof_buf; }
const uint16_t* adc_bua_buffer(void) { return bua_buf; }

void adc_stop(void)
{
    ADC1->CR &= ~ADC_CR_ADEN;
    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
}

void DMA1_Channel1_IRQHandler(void)
{
    if (DMA1->ISR & DMA_ISR_TCIF1) {
        DMA1->IFCR = DMA_IFCR_CTCIF1;
        if (ADC1->CFGR2 & ADC_CFGR2_ROVSE)
            bua_done = true;
        else
            tof_done = true;
    }
}