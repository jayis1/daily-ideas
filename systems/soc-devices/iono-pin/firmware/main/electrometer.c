/*
 * electrometer.c — ADA4530-1 TIA + ADS122U04 + STM32 ADC1 40 ksps capture
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * Faraday plate current (pA-nA) -> ADA4530-1 transimpedance amp (1e11 gain) ->
 * 3.0V single-ended output on PA0/ADC1_IN1.
 *
 * ADC1 triggered by TIM1_CH1 at 40 ksps, DMA circular buffer of 140 samples
 * (one drift-time sweep 0.5-3.5 ms). DMA half/full IRQs signal sweep ready.
 *
 * ADS122U04 (SPI2) is the auxiliary high-resolution path for slow monitoring
 * (battery, HV monitor backup); the high-speed drift-time capture uses ADC1.
 *
 * SPDX-License-Identifier: MIT
 */
#include "electrometer.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"

extern ADC_HandleTypeDef hadc1;
extern TIM_HandleTypeDef htim1;

static volatile bool g_ready = false;
static int16_t g_buf[EM_SAMPLES];

void electrometer_init(void)
{
    g_ready = false;
    /* ADC1: 12-bit, TIM1_TRGO trigger, DMA into g_buf */
    HAL_ADC_Start_DMA(&hadc1, (uint32_t *)g_buf, EM_SAMPLES);
    /* TIM1_CH1 configured for 40 ksps trigger in main() clock setup */
}

/* DMA half-transfer (not used) and full-transfer callbacks */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *h)
{
    if (h->Instance == ADC1) {
        g_ready = true;
    }
}

bool electrometer_sweep_ready(void)
{
    bool r = g_ready;
    g_ready = false;
    return r;
}

void electromer_capture(int16_t *out, uint16_t n)
{
    /* Blocking: arm DMA, wait for completion */
    g_ready = false;
    HAL_ADC_Stop_DMA(&hadc1);
    HAL_ADC_Start_DMA(&hadc1, (uint32_t *)g_buf, EM_SAMPLES);
    uint32_t to = 0;
    while (!g_ready && to < 100) { HAL_Delay(1); to++; }
    uint16_t cnt = (n < EM_SAMPLES) ? n : EM_SAMPLES;
    for (uint16_t i = 0; i < cnt; i++) {
        /* 12-bit ADC unsigned -> signed 16-bit centered at 2048 (zero current) */
        out[i] = (int16_t)((int)g_buf[i] - 2048);
    }
}

void electrometer_get(int16_t *out, uint16_t n)
{
    uint16_t cnt = (n < EM_SAMPLES) ? n : EM_SAMPLES;
    for (uint16_t i = 0; i < cnt; i++)
        out[i] = (int16_t)((int)g_buf[i] - 2048);
}