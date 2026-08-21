/*
 * sonar-cast / firmware / chirp.c
 * CHIRP waveform generation + matched-filter (pulse-compression) coefficient table.
 *
 * Generates a 150-250 kHz linear-FM chirp, Hamming-weighted, at 1 Msps.
 * Pre-computes the conjugate-time-reversed matched filter (500 taps) into
 * a split Q15 table for the Cortex-M4F SIMD FIR.
 */
#include "main.h"

/* Matched filter coefficients: 500 taps, split I/Q as Q15 (Hamming-weighted chirp). */
static q15_t mf_i[CHIRP_SAMPLES];   /* real part of matched filter */
static q15_t mf_q[CHIRP_SAMPLES];   /* imag part (Hilbert analytic) */

/* Transmit chirp phase-accumulator LUT (used by HRTIM DMA, 8-bit freq index). */
static uint16_t chirp_freq_lut[CHIRP_SAMPLES];

#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

void chirp_init(void)
{
    const double T   = (double)CHIRP_DURATION_US * 1e-6;   /* 0.5 ms */
    const double f0  = (double)CHIRP_F0;
    const double f1  = (double)CHIRP_F1;
    const double k   = (f1 - f0) / T;                       /* chirp rate Hz/s */
    const double fs  = (double)ADC_SAMPLE_RATE;
    const double dt  = 1.0 / fs;

    for (int n = 0; n < CHIRP_SAMPLES; n++) {
        double t  = n * dt;
        /* Linear-FM instantaneous phase: phi(t) = 2π(f0 t + 0.5 k t²) */
        double phase = 2.0 * M_PI * (f0 * t + 0.5 * k * t * t);
        /* Hamming window for -43 dB sidelobes */
        double w = CHIRP_HAMMING
            ? (0.54 - 0.46 * cos(2.0 * M_PI * n / (CHIRP_SAMPLES - 1)))
            : 1.0;

        double re = cos(phase) * w;
        double im = sin(phase) * w;

        /* Matched filter = conjugate + time-reverse of the transmit chirp.
           We store it time-reversed so FIR convolution = dot-product. */
        int idx = CHIRP_SAMPLES - 1 - n;
        mf_i[idx] = (q15_t)(re * 32767.0);
        mf_q[idx] = (q15_t)(-im * 32767.0);   /* conjugate: negate imag */

        /* Transmit LUT: instantaneous frequency in Hz → HRTIM period code.
           HRTIM period = SYS_CLK / (2 * f) for center-aligned PWM. */
        double f_inst = f0 + k * t;
        chirp_freq_lut[n] = (uint16_t)((double)SYS_CLK_HZ / (2.0 * f_inst));
    }
}

/* Return pointer to the transmit frequency LUT (for HRTIM DMA). */
const uint16_t *chirp_get_freq_lut(void) { return chirp_freq_lut; }

/* Return matched filter taps (I and Q split). */
void chirp_get_matched_filter(const q15_t **i, const q15_t **q)
{
    *i = mf_i;
    *q = mf_q;
}

/*
 * Pulse-compression FIR: convolve raw echo (real, centered around half-scale)
 * with the analytic matched filter, producing an envelope.
 *
 * Uses __SMLALD (dual 16-bit signed multiply-accumulate) for 2 samples/cycle.
 * Output is the magnitude |I + jQ| computed via CORDIC or sqrtf.
 */
void chirp_pulse_compress(const uint16_t *raw, uint32_t n_raw,
                          float *env_out, uint32_t n_env)
{
    const q15_t *mfi, *mfq;
    chirp_get_matched_filter(&mfi, &mfq);

    /* Center the raw ADC around 0 (remove DC / mid-scale offset) */
    const int32_t dc = ADC_MAX / 2;

    /* For each output sample, compute I = Σ raw·mf_i, Q = Σ raw·mf_q.
       We step by decimation factor to cover the full range window. */
    const uint32_t decim = n_raw / n_env;
    const uint32_t L = CHIRP_SAMPLES;

    for (uint32_t o = 0; o < n_env; o++) {
        uint32_t base = o * decim;
        if (base + L > n_raw) { env_out[o] = 0.0f; continue; }

        int64_t acc_i = 0, acc_q = 0;
        /* SIMD-friendly loop: process 2 taps per iteration */
        int n = 0;
        for (; n + 1 < (int)L; n += 2) {
            int32_t s0 = (int32_t)raw[base + n]     - dc;
            int32_t s1 = (int32_t)raw[base + n + 1] - dc;
            acc_i += (int64_t)s0 * mfi[n] + (int64_t)s1 * mfi[n + 1];
            acc_q += (int64_t)s0 * mfq[n] + (int64_t)s1 * mfq[n + 1];
        }
        if (n < (int)L) {
            int32_t s0 = (int32_t)raw[base + n] - dc;
            acc_i += (int64_t)s0 * mfi[n];
            acc_q += (int64_t)s0 * mfq[n];
        }

        /* Normalize: Q15 taps → /32768, sum of L taps → /L.
           Envelope = sqrt(I² + Q²) */
        double I = (double)acc_i / (32768.0 * L);
        double Q = (double)acc_q / (32768.0 * L);
        env_out[o] = (float)sqrt(I * I + Q * Q);
    }
}