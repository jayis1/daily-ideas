/*
 * adc.c — 500 ksps photodiode sampling via DMA + circular buffer
 *
 * ADC1 channel 1 (PA0) at 500 ksps, 12-bit, DMA circular into a
 * 1024-sample (2 ms window) buffer. Half-transfer and full-transfer
 * IRQs each process 512 samples (1 ms) through the pulse detector.
 */

#include "adc.h"
#include "pulse.h"
#include "stm32g474_conf.h"

static uint16_t dma_buf[ADC_DMA_BUF_LEN] __attribute__((aligned(32)));
static pulse_cb_t user_cb = NULL;
static volatile bool running = false;

void adc_init(void)
{
    /* PA0 analog */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER = (GPIOA->MODER & ~GPIO_MODER_MODE0);   /* analog */

    /* ADC1 */
    RCC->AHB2ENR |= RCC_AHB2ENR_ADC12EN;
    ADC1->CR |= ADC_CR_ADVREGEN;
    for (volatile int i = 0; i < 10000; ++i) ;
    ADC1->CR &= ~ADC_CR_DEEPPWD;
    ADC1->CR |= ADC_CR_ADCAL;
    while (ADC1->CR & ADC_CR_ADCAL) ;
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) ;

    /* ADC1 channel 1, 12-bit, continuous, DMA */
    ADC1->CFGR = ADC_CFGR_CONT | ADC_CFGR_DMAEN | ADC_CFGR_DMACFG;  /* circular DMA */
    ADC1->SQR1 = (1u << 6) | (1u << 9);  /* 1 conversion, channel 1 */
    ADC1->SMPR1 = (7u << ADC_SMPR1_SMP1_Pos);  /* max sample time, still ~500 ksps with 12-bit
                                                  and 20 MHz clock (14 cycles + 640.5 → ~640 cycles) */

    /* DMA1 channel 1 for ADC1 */
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA1EN;
    DMA1_Channel1->CPAR = (uint32_t)&ADC1->DR;
    DMA1_Channel1->CMAR = (uint32_t)dma_buf;
    DMA1_Channel1->CNDTR = ADC_DMA_BUF_LEN;
    DMA1_Channel1->CCR = DMA_CCR_MINC | DMA_CCR_CIRC | DMA_CCR_PSIZE_0
                       | DMA_CCR_MSIZE_0 | DMA_CCR_HTIE | DMA_CCR_TCIE
                       | DMA_CCR_EN;
    NVIC_EnableIRQ(DMA1_Channel1_IRQn);
}

void DMA1_Channel1_IRQHandler(void)
{
    if (DMA1->ISR & DMA_ISR_HTIF1) {
        DMA1->IFCR = DMA_IFCR_CHTIF1;
        if (running) pulse_process(dma_buf, ADC_DMA_BUF_LEN / 2);
    }
    if (DMA1->ISR & DMA_ISR_TCIF1) {
        DMA1->IFCR = DMA_IFCR_CTCIF1;
        if (running) pulse_process(dma_buf + ADC_DMA_BUF_LEN / 2, ADC_DMA_BUF_LEN / 2);
    }
}

void adc_start_sampling(pulse_cb_t cb)
{
    user_cb = cb;
    pulse_set_callback(cb);
    running = true;
    ADC1->CR |= ADC_CR_ADSTART;
}

void adc_stop_sampling(void)
{
    running = false;
    ADC1->CR |= ADC_CR_ADSTP;
    while (ADC1->CR & ADC_CR_ADSTP) ;
}

const uint16_t *adc_buffer(void) { return dma_buf; }
uint32_t adc_buffer_count(void) { return ADC_DMA_BUF_LEN; }