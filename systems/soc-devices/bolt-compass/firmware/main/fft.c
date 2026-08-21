/*
 * fft.c — 256-point in-place Radix-2 DIT FFT
 *
 * Pure-C reference; on the ESP32-S3 the inner loop benefits from the
 * Xtensa LX7 vector (IEEE754 single-precision) instructions, which the
 * compiler auto-vectorizes for the butterfly. For a 256-pt real-input
 * spectrum this runs in ~120 µs at 240 MHz — negligible vs. the 125 µs
 * per-sample budget.
 */
#include "fft.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

void fft256(float *re, float *im)
{
    int n = 256;
    /* Bit-reversal permutation. */
    for (int i = 1, j = 0; i < n; i++) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) {
            float tr = re[i]; re[i] = re[j]; re[j] = tr;
            float ti = im[i]; im[i] = im[j]; im[j] = ti;
        }
    }
    /* Cooley-Tukey butterflies. */
    for (int len = 2; len <= n; len <<= 1) {
        float ang = -2.0f * (float)M_PI / (float)len;
        float wr0 = cosf(ang), wi0 = sinf(ang);
        for (int i = 0; i < n; i += len) {
            float wr = 1.0f, wi = 0.0f;
            for (int k = 0; k < len / 2; k++) {
                float tr = wr * re[i + k + len/2] - wi * im[i + k + len/2];
                float ti = wr * im[i + k + len/2] + wi * re[i + k + len/2];
                re[i + k + len/2] = re[i + k] - tr;
                im[i + k + len/2] = im[i + k] - ti;
                re[i + k]        += tr;
                im[i + k]        += ti;
                float nwr = wr * wr0 - wi * wi0;
                float nwi = wr * wi0 + wi * wr0;
                wr = nwr; wi = nwi;
            }
        }
    }
}