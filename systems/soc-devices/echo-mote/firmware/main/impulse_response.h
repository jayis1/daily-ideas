/**
 * impulse_response.h — Impulse response extraction via overlap-save deconvolution
 *
 * Takes captured audio and the precomputed inverse chirp, and produces
 * the room impulse response using overlap-save FFT convolution.
 */

#ifndef IMPULSE_RESPONSE_H
#define IMPULSE_RESPONSE_H

#include <stdint.h>
#include <stddef.h>

/**
 * Extract the impulse response from a captured audio signal.
 *
 * Uses overlap-save convolution of captured signal with inverse chirp
 * to deconvolve the room response. The output is a float buffer
 * allocated in PSRAM that the caller must free.
 *
 * @param captured     Captured audio samples (int16)
 * @param num_samples  Number of samples in captured buffer
 * @param sample_rate  Sample rate in Hz
 * @return Pointer to float impulse response buffer (caller frees), or NULL on error
 */
float *impulse_response_extract(const int16_t *captured, uint32_t num_samples,
                                 uint32_t sample_rate);

/**
 * Compute Schroeder backward integration curve from an impulse response.
 *
 * @param ir           Impulse response (float)
 * @param num_samples  Number of samples
 * @param decay_curve  Output: dB decay curve (caller allocates, same length)
 * @return 0 on success
 */
int impulse_response_schroeder(const float *ir, uint32_t num_samples,
                                float *decay_curve);

#endif /* IMPULSE_RESPONSE_H */