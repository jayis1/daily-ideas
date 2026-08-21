/*
 * fft.h — 256-point Radix-2 FFT (vector-instr accelerated on ESP32-S3)
 */
#ifndef BOLT_COMPASS_FFT_H
#define BOLT_COMPASS_FFT_H

void fft256(float *re, float *im);
#endif