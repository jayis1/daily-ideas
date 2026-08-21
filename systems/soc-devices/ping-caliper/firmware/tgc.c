/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * tgc.c — Time-gain compensation ramp generation via DAC1 + DMA
 *
 * The AD8331 VGA gain is controlled by a 0–1 V analog voltage on its
 * GAIN pin. The STM32 DAC1_CH1 (PA0) outputs a time-varying ramp generated
 * from a lookup table by DMA, triggered by the HRTIM master timer so
 * every ramp restarts in lockstep with the transmit pulse.
 *
 * Gain (dB) = (V_gain − 0.04 V) × 50 dB/V × (V_gain in volts)
 *           → dB ≈ (dac_code/4095) × 50  (approximately)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "tgc.h"

static tgc_config_t g_tgc;
static uint16_t g_curve[TGC_POINTS];   /* DAC codes for the ramp */
static uint8_t  g_armed = 0;

void tgc_init(void)
{
    /* Enable DAC1 channel 1 (PA0) */
    RCC->AHB2ENR |= RCC_AHB2ENR_DAC1EN | RCC_AHB2ENR_DMA1EN;

    /* PA0 → analog (DAC1_OUT1) */
    GPIOA->MODER |= GPIO_MODER_MODE0;   /* analog = 11 */

    /* Enable DAC1 channel 1 with DMA + trigger */
    DAC1->MCR = 0;   /* default mode: output to pin, normal mode */
    DAC1->CR = DAC_CR_EN1 | DAC_CR_DMAEN1 | DAC_CR_TSEL1_0;  /* trig = TIM6 */
    /* DMA channel for DAC1 channel 1 */
    DMA1_Channel1->CCR = 0;   /* disable while configuring */
    DMA1_Channel1->CPAR  = (uint32_t)&DAC1->DHR12R1;
    DMA1_Channel1->CMAR  = (uint32_t)g_curve;
    DMA1_Channel1->CNDTR = TGC_POINTS;
    DMA1_Channel1->CCR = DMA_CCR_MINC | DMA_CCR_MSIZE_1 | DMA_CCR_PSIZE_1 |
                          DMA_CCR_CIRC | DMA_CCR_DIR | DMA_CCR_EN;

    g_tgc.shape        = TGC_SHAPE_LINEAR;
    g_tgc.start_db     = LNA_GAIN_MID_DB;
    g_tgc.end_db       = LNA_GAIN_MID_DB + 30.0f;
    g_tgc.window_us    = (uint16_t)CAPTURE_WINDOW_US_DEFAULT;
    g_tgc.lna_gain_idx = 1;

    /* Build the initial ramp */
    tgc_configure(&g_tgc);
}

void tgc_configure(const tgc_config_t *cfg)
{
    g_tgc = *cfg;

    /* Clamp */
    if (g_tgc.start_db < VGA_GAIN_MIN_DB) g_tgc.start_db = VGA_GAIN_MIN_DB;
    if (g_tgc.end_db   > VGA_GAIN_MAX_DB + LNA_GAIN_HIGH_DB)
        g_tgc.end_db = VGA_GAIN_MAX_DB + LNA_GAIN_HIGH_DB;

    /* Set LNA gain pins (3 GPIOs control AD8331 LNA gain range).
     * 0 = low (7.6 dB), 1 = mid (17.6 dB), 2 = high (22.6 dB).
     * These are 3 GPIO outputs (e.g. PA-pins) — simplified here. */
    /* (In full impl: drive the AD8331 LGA[1:0] pins.) */

    /* Build the ramp curve */
    for (uint16_t i = 0; i < TGC_POINTS; i++) {
        float t = (float)i / (float)(TGC_POINTS - 1);  /* 0..1 */
        float gain_db;
        switch (g_tgc.shape) {
        case TGC_SHAPE_FLAT:
            gain_db = g_tgc.start_db;
            break;
        case TGC_SHAPE_EXPONENTIAL:
            /* exp rise: gain(t) = start + (end-start)*(e^(kt)-1)/(e^k-1), k=3 */
            gain_db = g_tgc.start_db +
                      (g_tgc.end_db - g_tgc.start_db) *
                      (expf(3.0f * t) - 1.0f) / (expf(3.0f) - 1.0f);
            break;
        case TGC_SHAPE_CUSTOM:
            /* Custom curve points set individually; leave existing */
            gain_db = tgc_dac_to_db(g_curve[i]);
            break;
        case TGC_SHAPE_LINEAR:
        default:
            gain_db = g_tgc.start_db +
                      (g_tgc.end_db - g_tgc.start_db) * t;
            break;
        }
        g_curve[i] = tgc_db_to_dac(gain_db);
    }

    /* Update DAC DMA count if running */
    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
    DMA1_Channel1->CMAR  = (uint32_t)g_curve;
    DMA1_Channel1->CNDTR = TGC_POINTS;
    if (g_armed) DMA1_Channel1->CCR |= DMA_CCR_EN;
}

void tgc_get_config(tgc_config_t *cfg) { *cfg = g_tgc; }

void tgc_set_curve_point(uint16_t idx, float gain_db)
{
    if (idx >= TGC_POINTS) return;
    g_curve[idx] = tgc_db_to_dac(gain_db);
    g_tgc.shape = TGC_SHAPE_CUSTOM;
}

void tgc_arm(void)
{
    g_armed = 1;
    /* Restart DMA from the beginning of the curve and enable.
     * Triggered by TIM6 which is started by the HRTIM master sync. */
    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
    DMA1_Channel1->CNDTR = TGC_POINTS;
    DMA1_Channel1->CMAR  = (uint32_t)g_curve;
    DMA1_Channel1->CCR |= DMA_CCR_EN;
    DAC1->CR |= DAC_CR_EN1;
}

void tgc_disarm(void)
{
    g_armed = 0;
    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
    /* Output 0 V gain (min VGA gain) */
    DAC1->DHR12R1 = 0;
}

uint16_t tgc_db_to_dac(float gain_db)
{
    /* AD8331: 0 dB @ 50 mV, 50 dB/V → dB = (V - 0.05) * 50
     * V = dB/50 + 0.05, clamped 0..1 V.
     * DAC code = V/1.0 * 4095. */
    float v = gain_db / 50.0f + 0.05f;
    if (v < 0.0f) v = 0.0f;
    if (v > 1.0f) v = 1.0f;
    return (uint16_t)(v * 4095.0f);
}

float tgc_dac_to_db(uint16_t dac)
{
    float v = (float)dac / 4095.0f;   /* 0..1 V */
    float db = (v - 0.05f) * 50.0f;
    if (db < 0.0f) db = 0.0f;
    return db;
}