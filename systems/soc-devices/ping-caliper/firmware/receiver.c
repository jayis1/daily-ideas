/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * receiver.c — ADC1 (envelope) + ADC2 (RF) capture with DMA, timer-triggered
 *
 * Both ADCs are triggered by the HRTIM master event (same event that fires
 * the pulser), so each shot is captured at the same deterministic phase.
 * ADC1 captures the envelope/video at up to 5 Msps; ADC2 captures the RF
 * directly for probes ≤2 MHz.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "receiver.h"

static rx_config_t g_rx;
static volatile ascan_t g_buf_a;
static volatile ascan_t g_buf_b;
static volatile uint8_t g_active;      /* 0 = buf_a being filled, 1 = buf_b */
static volatile uint8_t g_ready;       /* 1 = a buffer is ready */
static volatile ascan_t *g_ready_buf;
static volatile uint8_t g_running;

void receiver_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_DMA1EN | RCC_AHB2ENR_ADC12EN |
                    RCC_AHB2ENR_GPIOAEN;

    /* PA2 (ADC1_IN3, envelope) and PA3 (ADC2_IN4, RF) → analog */
    GPIOA->MODER |= GPIO_MODER_MODE2 | GPIO_MODER_MODE3;  /* analog */

    /* ADC common setup */
    ADC12_COMMON->CCR = (2U << ADC_CCR_CKMODE_Pos);  /* async clock /4 */

    /* ADC1 (envelope) */
    ADC1->CR = 0;
    ADC1->CR |= ADC_CR_ADVREGEN;  /* enable regulator */
    /* Wait regulator startup (simplified) */
    for (volatile int i = 0; i < 1000; i++) { __NOP(); }
    ADC1->CR |= ADC_CR_CAL;        /* self-calibration */
    while (ADC1->CR & ADC_CR_CAL) { }
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) { }

    /* Configure channel 3 (PA2) */
    ADC1->SQR1 = (3U << ADC_SQR1_SQ1_Pos) | (1U << ADC_SQR1_L_Pos);  /* 1 conv */
    ADC1->SMPR1 = (2U << ADC_SMPR1_SMP3_Pos);  /* 6.5 cycles sampling */
    ADC1->CFGR = ADC_CFGR_DMAEN | ADC_CFGR_DMACFG |
                 (3U << ADC_CFGR_EXTSEL_Pos) |  /* trig = HRTIM */
                 ADC_CFGR_EXTEN_0;             /* rising edge */

    /* ADC2 (RF) — similar setup, channel 4 (PA3) */
    ADC2->CR = 0;
    ADC2->CR |= ADC_CR_ADVREGEN;
    for (volatile int i = 0; i < 1000; i++) { __NOP(); }
    ADC2->CR |= ADC_CR_CAL;
    while (ADC2->CR & ADC_CR_CAL) { }
    ADC2->CR |= ADC_CR_ADEN;
    while (!(ADC2->ISR & ADC_ISR_ADRDY)) { }

    ADC2->SQR1 = (4U << ADC_SQR1_SQ1_Pos) | (1U << ADC_SQR1_L_Pos);
    ADC2->SMPR1 = (1U << ADC_SMPR1_SMP4_Pos);
    ADC2->CFGR = ADC_CFGR_DMAEN | ADC_CFGR_DMACFG |
                 (3U << ADC_CFGR_EXTSEL_Pos) |
                 ADC_CFGR_EXTEN_0;

    g_rx.window_us       = (uint16_t)CAPTURE_WINDOW_US_DEFAULT;
    g_rx.sample_count    = (uint16_t)(CAPTURE_WINDOW_US_DEFAULT *
                                       (ADC_SAMPLE_RATE_HZ / 1000000.0f));
    g_rx.source          = 0;
    g_rx.trigger_channel = 0;

    g_active = 0;
    g_ready = 0;
    g_running = 0;
}

void rx_configure(const rx_config_t *cfg)
{
    g_rx = *cfg;
    if (g_rx.sample_count > MAX_SAMPLES) g_rx.sample_count = MAX_SAMPLES;
    if (g_rx.sample_count < MIN_SAMPLES) g_rx.sample_count = MIN_SAMPLES;
}

void rx_get_config(rx_config_t *cfg) { *cfg = g_rx; }

static void adc_dma_setup(void *buf, uint16_t count, int adc_num)
{
    /* DMA channel for ADC1 = DMA1 Channel 1; for ADC2 = DMA1 Channel 2 */
    DMA_Channel_TypeDef *ch = adc_num == 1 ? DMA1_Channel1 : DMA1_Channel2;
    uint32_t par = adc_num == 1 ? (uint32_t)&ADC1->DR : (uint32_t)&ADC2->DR;

    ch->CCR = 0;
    ch->CPAR = par;
    ch->CMAR = (uint32_t)buf;
    ch->CNDTR = count;
    /* 16-bit transfers, memory increment, circular, high priority */
    ch->CCR = DMA_CCR_MINC | DMA_CCR_MSIZE_0 | DMA_CCR_PSIZE_0 |
              DMA_CCR_CIRC | DMA_CCR_PL_1 | DMA_CCR_EN;
}

void rx_start_continuous(void)
{
    g_running = 1;
    g_ready = 0;
    g_active = 0;

    uint16_t count = g_rx.sample_count;
    if (count > MAX_SAMPLES) count = MAX_SAMPLES;

    /* Configure ADC1 DMA into buf_a */
    adc_dma_setup((void *)g_buf_a.envelope, count, 1);
    if (g_rx.source == 2) {
        adc_dma_setup((void *)g_buf_a.rf, count, 2);
    }

    /* Start ADC1 conversion */
    ADC1->CR |= ADC_CR_ADSTART;
    if (g_rx.source == 2) ADC2->CR |= ADC_CR_ADSTART;
}

void rx_stop_continuous(void)
{
    g_running = 0;
    ADC1->CR |= ADC_CR_ADSTP;
    ADC2->CR |= ADC_CR_ADSTP;
    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
    DMA1_Channel2->CCR &= ~DMA_CCR_EN;
}

uint8_t rx_capture_single(ascan_t *out)
{
    if (!out) return 0;
    g_running = 1;

    uint16_t count = g_rx.sample_count;
    if (count > MAX_SAMPLES) count = MAX_SAMPLES;

    /* Setup DMA for one-shot (not circular) */
    DMA1_Channel1->CCR = 0;
    DMA1_Channel1->CPAR = (uint32_t)&ADC1->DR;
    DMA1_Channel1->CMAR = (uint32_t)out->envelope;
    DMA1_Channel1->CNDTR = count;
    DMA1_Channel1->CCR = DMA_CCR_MINC | DMA_CCR_MSIZE_0 | DMA_CCR_PSIZE_0 |
                         DMA_CCR_PL_1 | DMA_CCR_TCIE | DMA_CCR_EN;

    ADC1->CR |= ADC_CR_ADSTART;

    /* Wait for DMA completion (simplified; in real impl use IRQ) */
    uint32_t timeout = SystemCoreClock;
    while (DMA1_Channel1->CNDTR > 0 && timeout--) { __NOP(); }

    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
    ADC1->CR |= ADC_CR_ADSTP;
    out->count = count;
    out->valid = 1;
    g_running = 0;
    return 1;
}

uint8_t rx_get_latest(ascan_t *out)
{
    if (!out || !g_ready) return 0;
    /* Copy the ready buffer (double-buffer swap) */
    *out = *g_ready_buf;
    g_ready = 0;
    return 1;
}

/* DMA end-of-transfer ISR — swaps double buffer and signals ready. */
void DMA1_Channel1_IRQHandler(void)
{
    if (DMA1->ISR & DMA_ISR_TCIF1) {
        DMA1->IFCR = DMA_IFCR_CTCIF1;
        /* Buffer A filled → swap to B */
        if (g_active == 0) {
            g_ready_buf = &g_buf_a;
            g_active = 1;
            adc_dma_setup((void *)g_buf_b.envelope, g_rx.sample_count, 1);
        } else {
            g_ready_buf = &g_buf_b;
            g_active = 0;
            adc_dma_setup((void *)g_buf_a.envelope, g_rx.sample_count, 1);
        }
        g_ready_buf->count = g_rx.sample_count;
        g_ready_buf->valid = 1;
        g_ready = 1;
    }
}