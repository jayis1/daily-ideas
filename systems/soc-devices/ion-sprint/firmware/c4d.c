/*
 * c4d.c — Contactless conductivity detection (C4D)
 *
 * C4D measures the conductivity of the solution inside the capillary
 * at the detection window, without galvanic contact. Two cylindrical
 * copper electrodes (2 mm wide, 1 mm gap) wrap around the capillary.
 *
 * Driver electrode (E1): DAC2 generates 100 kHz AC (±1.65 V centered
 * on 1.65 V VREF/2). The AC couples through the capillary wall
 * (dielectric) to the solution, then to the pickup electrode.
 *
 * Pickup electrode (E2): feeds OPA656 JFET op-amp (transimpedance,
 * 1 MΩ feedback) → 4th-order Bessel BPF (90–110 kHz) → ADC1 (PA0).
 *
 * Lock-in demodulation: the STM32 multiplies the ADC signal by
 * cos(2π·100k·t) and sin(2π·100k·t) (I/Q), low-pass filters (τ=10 ms),
 * and computes R = sqrt(I² + Q²) — the amplitude envelope. When an
 * ion zone with different conductivity than the BGE passes between
 * the electrodes, the admittance changes, modulating R. The resulting
 * time series is the electropherogram at 100 Hz.
 *
 * Guard shield (PB10): driven at driver potential to minimize
 * parasitic capacitance to ground.
 */

#include "c4d.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <math.h>

/* Quarter-wave sine lookup table (16 entries, 0–90°) */
static const float sine_q[16] = {
    0.000f, 0.098f, 0.195f, 0.290f, 0.383f, 0.471f, 0.556f, 0.634f,
    0.707f, 0.773f, 0.831f, 0.882f, 0.924f, 0.957f, 0.981f, 0.995f,
};

/* Lock-in state */
static float i_acc = 0.0f, q_acc = 0.0f;
static uint32_t sample_count = 0;
static uint32_t demod_count = 0;
static float   *eph_buffer = NULL;
static uint32_t eph_max = 0;
static bool     acquiring = false;

/* IIR low-pass filter state (2nd-order, τ=10 ms, 100 Hz output) */
typedef struct {
    float x1, x2, y1, y2;
    float b0, b1, b2, a1, a2;
} iir_lp_t;

static iir_lp_t lp_i = {0}, lp_q = {0};

static void iir_lp_init(iir_lp_t *f)
{
    /* 2nd-order Butterworth, fc = 1/(2π·τ) = 15.9 Hz
     * At 200 kHz sample rate (lock-in input), fc/fs = 7.95e-5
     * Coefficients precomputed for stability.
     */
    f->b0 = 1.0e-9f;  f->b1 = 2.0e-9f;  f->b2 = 1.0e-9f;
    f->a1 = -1.999968f; f->a2 = 0.999968f;
    f->x1 = f->x2 = f->y1 = f->y2 = 0.0f;
}

static float iir_lp_run(iir_lp_t *f, float x)
{
    float y = f->b0 * x + f->b1 * f->x1 + f->b2 * f->x2
              - f->a1 * f->y1 - f->a2 * f->y2;
    f->x2 = f->x1; f->x1 = x;
    f->y2 = f->y1; f->y1 = y;
    return y;
}

void c4d_init(void)
{
    /* DAC2 on PA2: 100 kHz AC excitation
     * Generate 4-point sine: 0, 1, 0, -1 (crude sine) → filtered by BPF
     * In practice: DMA from sine table to DAC at 400 kHz (4× carrier)
     */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (2u * 2u))) | (0b11 << (2u * 2u));
    RCC->APB1ENR1 |= RCC_APB1ENR1_DAC1EN;
    DAC1->MCR |= DAC_MCR_MODE2_1;  /* DAC2 normal mode, output on PA2 */
    DAC1->CR |= DAC_CR_EN2;
    DAC1->DHR12R2 = 2048;  /* Center on VREF/2 = 1.65 V */

    /* PB10: guard shield output (driven at driver potential) */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->MODER = (GPIOB->MODER & ~(3u << (10u * 2u))) | (1u << (10u * 2u));

    /* ADC1 on PA0: 200 kHz sample rate
     * Real code configures ADC1 with DMA circular buffer at 200 kHz.
     * Placeholder: set up channel 1 (PA0), 12-bit, continuous mode.
     */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    GPIOA->MODER &= ~(3u << (0u * 2u));  /* Analog input */

    iir_lp_init(&lp_i);
    iir_lp_init(&lp_q);

    acquiring = false;
    eph_buffer = NULL;
    eph_max = 0;
    sample_count = 0;
}

void c4d_start_acquisition(float *buffer, uint32_t max_samples)
{
    eph_buffer = buffer;
    eph_max = max_samples;
    sample_count = 0;
    demod_count = 0;
    i_acc = q_acc = 0.0f;
    iir_lp_init(&lp_i);
    iir_lp_init(&lp_q);
    acquiring = true;

    /* Enable DAC2 excitation + ADC1 DMA (placeholder) */
    DAC1->DHR12R2 = 2048;  /* Start at center */
}

void c4d_stop_acquisition(void)
{
    acquiring = false;
    /* Disable DAC2 excitation */
    DAC1->DHR12R2 = 2048;  /* Return to center (no AC) */
}

bool c4d_is_acquiring(void)
{
    return acquiring && (sample_count < eph_max);
}

uint32_t c4d_get_sample_count(void)
{
    return sample_count;
}

/* Process a block of raw ADC samples through the lock-in demodulator.
 * Called at 200 kHz rate in blocks of ~200 samples (1 ms each).
 * After demod + low-pass, one electropherogram point per 10 ms → 100 Hz.
 */
void c4d_process_block(const uint16_t *raw, uint32_t count)
{
    if (!acquiring || eph_buffer == NULL) return;

    for (uint32_t n = 0; n < count; n++) {
        /* Convert ADC to voltage: 0–4095 → 0–3.0 V, remove DC (1.65 V) */
        float v = ((float)raw[n] / 4095.0f) * C4D_ADC_FULLSCALE - 1.65f;

        /* Generate reference phase at 100 kHz (4-point: cos, sin cycle) */
        /* At 200 kHz ADC, each sample = 5 µs. 100 kHz period = 10 µs = 2 samples.
         * So we alternate: sample 0 = cos=1, sin=0; sample 1 = cos=0, sin=1
         * (simplified square-wave lock-in; real code uses CORDIC sine table)
         */
        float phase = (float)demod_count * 2.0f * 3.14159265f
                      * (C4D_EXCIT_FREQ_HZ / (float)C4D_ADC_RATE_HZ);
        float ref_i = cosf(phase);
        float ref_q = sinf(phase);
        demod_count++;

        /* I/Q multiply */
        i_acc += v * ref_i;
        q_acc += v * ref_q;

        /* Every 2000 samples (10 ms at 200 kHz) → one electropherogram point */
        if (demod_count >= 2000) {
            float i_val = i_acc / (float)demod_count;
            float q_val = q_acc / (float)demod_count;

            /* Low-pass filter I/Q channels */
            float i_filt = iir_lp_run(&lp_i, i_val);
            float q_filt = iir_lp_run(&lp_q, q_val);

            /* Amplitude = sqrt(I² + Q²) */
            float r = sqrtf(i_filt * i_filt + q_filt * q_filt);

            /* Store electropherogram point */
            if (sample_count < eph_max) {
                eph_buffer[sample_count++] = r;
            }

            /* Reset accumulators */
            i_acc = q_acc = 0.0f;
            demod_count = 0;
        }
    }
}