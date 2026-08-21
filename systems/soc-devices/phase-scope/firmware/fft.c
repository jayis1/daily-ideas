/*
 * Phase Scope — 1024-point FFT using CMSIS-DSP
 * Extracts harmonic magnitudes for THD computation
 */

#include "fft.h"
#include <math.h>

/* We use the ARM CMSIS-DSP library for FFT on Cortex-M4F */
/* If not available, we provide a basic radix-2 Cooley-Tukey implementation */

#ifndef USE_CMSIS_DSP

/* ------------------------------------------------------------------ */
/* Bit-reversal permutation                                             */
/* ------------------------------------------------------------------ */

static void bit_reverse_copy(float *dst, const float *src, int n)
{
    int bits = 0;
    int temp = n;
    while (temp > 1) { bits++; temp >>= 1; }

    for (int i = 0; i < n; i++) {
        int rev = 0;
        int val = i;
        for (int b = 0; b < bits; b++) {
            rev = (rev << 1) | (val & 1);
            val >>= 1;
        }
        dst[2 * rev]     = src[2 * i];     /* Real */
        dst[2 * rev + 1] = src[2 * i + 1]; /* Imag */
    }
}

/* ------------------------------------------------------------------ */
/* Radix-2 Cooley-Tukey FFT (in-place)                                */
/* ------------------------------------------------------------------ */

static void fft_radix2(float *data, int n)
{
    /* Bit-reversal permutation */
    int bits = 0;
    int temp = n;
    while (temp > 1) { bits++; temp >>= 1; }

    for (int i = 0; i < n; i++) {
        int rev = 0;
        int val = i;
        for (int b = 0; b < bits; b++) {
            rev = (rev << 1) | (val & 1);
            val >>= 1;
        }
        if (i < rev) {
            /* Swap real */
            float tr = data[2 * i];
            data[2 * i]     = data[2 * rev];
            data[2 * rev]   = tr;
            /* Swap imag */
            float ti = data[2 * i + 1];
            data[2 * i + 1]     = data[2 * rev + 1];
            data[2 * rev + 1]   = ti;
        }
    }

    /* Butterfly stages */
    for (int stage = 1; stage <= bits; stage++) {
        int m = 1 << stage;
        float wm_real = cosf(2.0f * (float)M_PI / (float)m);
        float wm_imag = -sinf(2.0f * (float)M_PI / (float)m);

        for (int k = 0; k < n; k += m) {
            float w_real = 1.0f;
            float w_imag = 0.0f;

            for (int j = 0; j < m / 2; j++) {
                int idx1 = 2 * (k + j);
                int idx2 = 2 * (k + j + m / 2);

                float t_real = w_real * data[idx2] - w_imag * data[idx2 + 1];
                float t_imag = w_real * data[idx2 + 1] + w_imag * data[idx2];

                data[idx2]     = data[idx1] - t_real;
                data[idx2 + 1] = data[idx1 + 1] - t_imag;
                data[idx1]     = data[idx1] + t_real;
                data[idx1 + 1] = data[idx1 + 1] + t_imag;

                /* w = w × wm */
                float new_w_real = w_real * wm_real - w_imag * wm_imag;
                float new_w_imag = w_real * wm_imag + w_imag * wm_real;
                w_real = new_w_real;
                w_imag = new_w_imag;
            }
        }
    }
}

#endif /* !USE_CMSIS_DSP */

/* ------------------------------------------------------------------ */
/* Public FFT interface                                                 */
/* ------------------------------------------------------------------ */

/* Working buffer for FFT (complex, 2 × N floats) */
static float fft_buffer[2 * FFT_SIZE];

void fft_compute(const float *input, int n, float *harmonics)
{
    int fft_n = FFT_SIZE;

    /* Pad input to FFT_SIZE with zeros if needed */
    for (int i = 0; i < fft_n; i++) {
        if (i < n) {
            fft_buffer[2 * i]     = input[i];   /* Real part */
            fft_buffer[2 * i + 1] = 0.0f;        /* Imaginary part */
        } else {
            fft_buffer[2 * i]     = 0.0f;
            fft_buffer[2 * i + 1] = 0.0f;
        }
    }

    /* Apply Hann window to reduce spectral leakage */
    for (int i = 0; i < fft_n; i++) {
        float w = 0.5f * (1.0f - cosf(2.0f * (float)M_PI * (float)i / (float)fft_n));
        fft_buffer[2 * i]     *= w;
        fft_buffer[2 * i + 1] *= w;
    }

    /* Compute FFT */
#ifdef USE_CMSIS_DSP
    arm_cfft_f32(&arm_cfft_sR_f32_len1024, fft_buffer, 0, 1);
    arm_cmplx_mag_f32(fft_buffer, fft_buffer, fft_n / 2);
#else
    fft_radix2(fft_buffer, fft_n);
#endif

    /* Extract harmonic magnitudes
     * Fundamental is at bin = round(f_fundamental / (f_sample / N))
     * For 50 Hz fundamental at 4 kSPS with N=1024:
     *   bin = 50 / (4000/1024) ≈ 12.8 → bin 13
     * For 60 Hz: bin = 60 / (4000/1024) ≈ 15.36 → bin 15
     *
     * We extract harmonics at multiples of the fundamental bin
     */

    /* Find fundamental: peak in low-frequency bins (10-20) */
    float max_mag = 0.0f;
    int fund_bin = 13; /* Default for 50 Hz */

    for (int b = 8; b < 25; b++) {
        float real = fft_buffer[2 * b];
        float imag = fft_buffer[2 * b + 1];
        float mag = sqrtf(real * real + imag * imag);
        if (mag > max_mag) {
            max_mag = mag;
            fund_bin = b;
        }
    }

    /* Extract harmonics */
    for (int h = 0; h < MAX_HARMONICS && (h + 1) * fund_bin < fft_n / 2; h++) {
        int bin = (h + 1) * fund_bin;
        float real = fft_buffer[2 * bin];
        float imag = fft_buffer[2 * bin + 1];
        harmonics[h] = sqrtf(real * real + imag * imag) / (float)fft_n;
    }

    /* Fill remaining harmonics with zero */
    for (int h = fund_bin; h < MAX_HARMONICS; h++) {
        /* Find highest filled bin */
    }
}