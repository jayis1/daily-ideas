/*
 * rx_chain.c — AD8331 VGA + TGC ramp + BPF control
 *
 * The AD8331 VGA gain is set by a combination of:
 *   - 2-bit GPIO mode (PB6/PB7): sets the gain range (LO/MID/HI)
 *   - Analog voltage on the GAIN pin (DAC1_OUT1, PA1): fine gain within range
 *
 * The TGC (time-gain compensation) ramp compensates for tissue attenuation
 * with depth: the deeper the ultrasound travels, the more it's attenuated,
 * so the VGA gain increases over the capture window to keep the signal
 * in the ADC's dynamic range.
 */

#include "rx_chain.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"

static float cur_gain_db = TGC_RAMP_START_DB;

void rx_chain_init(void)
{
    /* PB6, PB7: AD8331 gain mode select (outputs) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (6u * 2u))) | (1u << (6u * 2u));
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (7u * 2u))) | (1u << (7u * 2u));
    /* Default: MID range (PB6=0, PB7=1) */
    GPIOB->BSRR = (1u << (6u + 16u));   /* PB6 = low */
    GPIOB->BSRR = (1u << 7u);           /* PB7 = high */

    /* PA1: DAC1_OUT1 (TGC ramp control) — analog output */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (1u * 2u))) | (3u << (1u * 2u)); /* Analog */
    GPIOA->AFR[0] = (GPIOA->AFR[0] & ~(0xFu << (1u * 4u)));

    /* Enable DAC1 clock */
    RCC->AHB1ENR |= RCC_AHB1ENR_DAC1EN;
    DAC1->CR |= DAC_CR_EN1;
    DAC1->DHR12R1 = 0;   /* Start at 0 V (minimum gain) */

    cur_gain_db = TGC_RAMP_START_DB;
}

void rx_chain_set_gain_db(float gain_db)
{
    if (gain_db < VGA_GAIN_MIN_DB) gain_db = VGA_GAIN_MIN_DB;
    if (gain_db > VGA_GAIN_MAX_DB) gain_db = VGA_GAIN_MAX_DB;
    cur_gain_db = gain_db;

    /* AD8331 gain (approx): GAIN pin voltage 0.0–1.0 V maps to 0–48 dB
     * (in MID range). DAC1 outputs 0–3.0 V → divide by 3 for 0–1 V.
     * DAC code = (gain_db / 48.0) × 1.0 / 3.0 × 4095
     */
    float v_gain = gain_db / VGA_GAIN_MAX_DB;   /* 0.0–1.0 V */
    float v_dac  = v_gain * 3.0f;                /* 0.0–3.0 V at DAC */
    uint32_t code = (uint32_t)((v_dac / ADC_FULLSCALE_V) * 4095.0f);
    if (code > 4095) code = 4095;
    DAC1->DHR12R1 = code;
}

void rx_chain_set_tgc_ramp(float start_db, float end_db)
{
    /* TGC ramp: DAC1 sweeps from start_db to end_db over the capture window.
     * For ToF (32 ms at 3.6 Msps), the ramp is fast.
     * For BUA (50 ms oversampled), the ramp is slower.
     *
     * Simplified: set to midpoint gain for the burst; a real implementation
     * would DMA a ramp table to DAC1.
     */
    float mid = (start_db + end_db) * 0.5f;
    rx_chain_set_gain_db(mid);
}

float rx_chain_get_gain_db(void) { return cur_gain_db; }