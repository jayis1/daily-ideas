/*
 * pga.c — PGA204 + PGA113 programmable-gain front-end control
 *
 * The PGA204 is an instrumentation amplifier with 4 gain settings
 * (1×/2×/4×/8×) selected by 3 digital pins A0..A2. The PGA113 is a
 * low-noise PGA with 8 gain settings (1×/2×/4×/8×/16×/32×/64×/128×).
 * Cascaded, they give 1×–1024× programmable gain (8×128 = 1024).
 *
 * Pin mapping on STM32G491:
 *   PGA204 A0 = PB2, A1 = PB3, A2 = PB4
 *   PGA113 A0 = PB5, A1 = PB6, A2 = PB7
 */

#include "stm32g491_conf.h"
#include "pga.h"
#include "adc.h"

static pga_gain_t cur_gain = PGA_GAIN_1;
static const float gain_values[] = {
    1.0f, 2.0f, 4.0f, 8.0f, 16.0f, 32.0f, 64.0f, 128.0f, 256.0f, 512.0f, 1024.0f
};

void pga_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    /* All PGA pins as push-pull outputs, default low (gain = 1×) */
    GPIOB->MODER = (GPIOB->MODER & ~(0x3FFFU << (2*2)))
                | (0x1555U << (2*2));   /* PB2..PB7 = output */
    GPIOB->OTYPER &= ~(0x3FU << 2);
    GPIOB->BSRR = (0x3FU << (2 + 16));  /* reset PB2..PB7 */
    cur_gain = PGA_GAIN_1;
}

static void pga_write(pga_gain_t g)
{
    /* Decompose into stage1 (PGA204: 0..3) and stage2 (PGA113: 0..7) */
    uint32_t s1 = 0, s2 = 0;
    if (g <= PGA_GAIN_8) {
        s1 = (uint32_t)g;     /* 1×..8× via PGA204, PGA113 = 1× */
        s2 = 0;
    } else {
        s1 = 3;                /* PGA204 = 8× */
        s2 = (uint32_t)g - 3; /* PGA113 = 2×..128× → 1..7 */
    }
    /* PGA204: A0,A1,A2 select 1×/2×/4×/8× (binary-coded, 0..3) */
    GPIOB->BSRR = (0x7U << (2 + 16));   /* clear PB2..PB4 */
    GPIOB->BSRR = ((s1 & 0x7U) << 2);
    /* PGA113: A0,A1,A2 select 1×..128× (binary-coded, 0..7) */
    GPIOB->BSRR = (0x7U << (5 + 16));   /* clear PB5..PB7 */
    GPIOB->BSRR = ((s2 & 0x7U) << 5);
}

void pga_set_gain(pga_gain_t g)
{
    if (g < PGA_GAIN_1)    g = PGA_GAIN_1;
    if (g > PGA_GAIN_1024) g = PGA_GAIN_1024;
    cur_gain = g;
    pga_write(g);
}

pga_gain_t pga_get(void) { return cur_gain; }
float pga_get_gain(void) { return gain_values[cur_gain]; }

bool pga_auto_range(void)
{
    float v = adc_read_signal_monitor();
    float fs = 10.0f;   /* ±10 V full-scale */
    float ratio = v / fs;
    pga_gain_t newg = cur_gain;
    if (ratio > 0.8f && cur_gain > PGA_GAIN_1) {
        newg = (pga_gain_t)(cur_gain - 1);   /* too hot, reduce gain */
    } else if (ratio < 0.3f && cur_gain < PGA_GAIN_1024) {
        newg = (pga_gain_t)(cur_gain + 1);   /* too quiet, increase gain */
    }
    if (newg != cur_gain) {
        pga_set_gain(newg);
        return true;
    }
    return false;
}