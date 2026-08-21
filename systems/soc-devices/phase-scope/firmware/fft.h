/*
 * Phase Scope — FFT header
 */

#ifndef FFT_H
#define FFT_H

#include <stdint.h>

#define FFT_SIZE 1024
#define MAX_HARMONICS 50

void fft_compute(const float *input, int n, float *harmonics);

#endif /* FFT_H */