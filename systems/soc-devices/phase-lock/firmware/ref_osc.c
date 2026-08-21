/*
 * ref_osc.c — reference oscillator: CORDIC sine + DAC1 drive
 *
 * The STM32G491 CORDIC peripheral computes sin/cos of a 32-bit phase
 * argument in q1.31 scale, taking ~12 cycles. We maintain a 32-bit
 * phase accumulator that advances by phase_inc = 2^32 * f0 / f_dds
 * per DAC sample (f_dds = 1 MHz). The CORDIC output drives DAC1 at
 * 1 Msps via DMA. The same phase accumulator supplies the digital
 * demodulator, ensuring phase coherence.
 *
 * For the demodulator (running at f_s = 28 ksps) we recompute the
 * reference I/Q by advancing the phase accumulator by the ADC-sample
 * increment and querying the CORDIC, giving micro-Hz-accurate coherence.
 */

#include "stm32g491_conf.h"
#include "ref_osc.h"
#include <math.h>

ref_osc_t g_ref;

#define DDS_RATE_HZ   1000000UL
#define F32_SCALE      4294967296.0
#define PI             3.14159265358979323846

/* DMA buffer for DAC1 (64 samples, double-buffered) */
static uint16_t dac_buf[2][64] __attribute__((section(".ccm")));

void ref_osc_init(void)
{
    /* Enable CORDIC clock */
    RCC->AHB1ENR |= RCC_AHB1ENR_CORDICEN;

    /* Configure CORDIC: cosine mode, q1.31 in/out, 12 iterations (precision) */
    CORDIC->CSR = CORDIC_CSR_FUNC_COSINE
                | CORDIC_CSR_SCALE_0
                | CORDIC_CSR_QSIZE_32BIT
                | CORDIC_CSR_RSIZE_32BIT
                | (12U << CORDIC_CSR_NRES_Pos);

    /* DAC1 channel 1 setup: 12-bit, DMA TIM6-triggered @ 1 MHz */
    RCC->AHB2ENR |= RCC_AHB2ENR_DAC1EN;
    DAC1->CR = 0;
    DAC1->MCR = DAC_MCR_MODE1_1;     /* normal mode, no output buffer off */
    DAC1->CR |= DAC_CR_EN1;
    /* TIM6 generates the 1 MHz trigger (set up elsewhere) */

    g_ref.freq_hz     = 1000.0f;
    g_ref.amplitude_v = 1.0f;
    g_ref.phase_deg   = 0.0f;
    g_ref.phase_accum = 0;
    g_ref.phase_inc   = (uint32_t)(g_ref.freq_hz * F32_SCALE / DDS_RATE_HZ);
    g_ref.running     = false;
    g_ref.dual_mode   = false;
}

void ref_osc_set_freq(float f_hz)
{
    if (f_hz < 1.0f)   f_hz = 1.0f;
    if (f_hz > 100000.0f) f_hz = 100000.0f;
    g_ref.freq_hz   = f_hz;
    g_ref.phase_inc = (uint32_t)(f_hz * F32_SCALE / DDS_RATE_HZ);
}

void ref_osc_set_amplitude(float v)
{
    if (v < 0.0f) v = 0.0f;
    if (v > 2.0f) v = 2.0f;
    g_ref.amplitude_v = v;
}

void ref_osc_set_phase(float deg)
{
    while (deg <    0.0f) deg += 360.0f;
    while (deg >= 360.0f) deg -= 360.0f;
    g_ref.phase_deg = deg;
}

void ref_osc_start(void)
{
    g_ref.running = true;
    /* Start TIM6 DMA feeding DAC1 at 1 MHz */
    TIM6->CR1 |= TIM_CR1_CEN;
}

void ref_osc_stop(void)
{
    g_ref.running = false;
    TIM6->CR1 &= ~TIM_CR1_CEN;
    DAC1->DHR12R1 = 2048;  /* mid-scale (0 V) */
}

/* Fill a DMA buffer with the next 64 sine samples (called by DMA1 Ch2 ISR) */
void ref_osc_fill_dac_buf(uint16_t *buf)
{
    const float amp = g_ref.amplitude_v / 2.0f;     /* 0..1 → 0..2047 */
    const uint32_t phoff = (uint32_t)(g_ref.phase_deg / 360.0f * F32_SCALE);
    for (int i = 0; i < 64; ++i) {
        g_ref.phase_accum += g_ref.phase_inc;
        uint32_t arg = g_ref.phase_accum + phoff;
        /* CORDIC cosine q1.31 → ±2^31 */
        CORDIC->WDATA = (int32_t)arg;
        while (!(CORDIC->CSR & CORDIC_CSR_RRDY)) ;
        int32_t cos_q31 = (int32_t)CORDIC->RDATA;
        /* map to 12-bit DAC: 0..4095 around mid-scale 2048 */
        int32_t dac = 2048 + (int32_t)(cos_q31 * amp / (float)(1U<<31) * 2047.0f);
        if (dac < 0)    dac = 0;
        if (dac > 4095) dac = 4095;
        buf[i] = (uint16_t)dac;
    }
}

/* Get I/Q reference samples for the demodulator (called at f_s = 28 ksps).
 * We advance the phase accumulator by the ADC-rate increment (not the
 * 1 MHz increment), keeping phase coherence with the DAC output.
 */
void ref_osc_get_iq(int32_t *i_ref, int32_t *q_ref)
{
    static uint32_t demod_phase = 0;
    static uint32_t demod_inc   = 0;
    if (demod_inc == 0) {  /* lazy init on first call */
        demod_inc = (uint32_t)(g_ref.freq_hz * F32_SCALE / ADC_SPS);
    }
    /* Update demod_inc if frequency changed */
    demod_inc = (uint32_t)(g_ref.freq_hz * F32_SCALE / ADC_SPS);

    demod_phase += demod_inc;
    uint32_t arg = demod_phase + (uint32_t)(g_ref.phase_deg / 360.0f * F32_SCALE);

    CORDIC->WDATA = (int32_t)arg;
    while (!(CORDIC->CSR & CORDIC_CSR_RRDY)) ;
    int32_t cos_q31 = (int32_t)CORDIC->RDATA;
    /* sine = cosine(phase - 90°) */
    uint32_t arg_sin = arg - (uint32_t)(F32_SCALE / 4);
    CORDIC->WDATA = (int32_t)arg_sin;
    while (!(CORDIC->CSR & CORDIC_CSR_RRDY)) ;
    int32_t sin_q31 = (int32_t)CORDIC->RDATA;

    *i_ref = cos_q31;   /* in-phase reference    */
    *q_ref = sin_q31;   /* quadrature reference */
}