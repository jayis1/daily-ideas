/**
 * chirp_generator.h — Logarithmic swept-sine (chirp) synthesis
 *
 * Generates a log-swept sine from fmin to fmax over a given duration,
 * and precomputes the inverse chirp for impulse response deconvolution.
 */

#ifndef CHIRP_GENERATOR_H
#define CHIRP_GENERATOR_H

#include <stdint.h>
#include <stddef.h>

/* Default chirp parameters */
#define CHIRP_FMIN_HZ       20.0f
#define CHIRP_FMAX_HZ       20000.0f
#define CHIRP_DURATION_S    5.0f
#define CHIRP_SAMPLE_RATE   48000

/**
 * Initialize the chirp generator.
 * Precomputes the inverse chirp in PSRAM at the given sample rate.
 * Must be called once before any playback.
 *
 * @param sample_rate  Sample rate in Hz (typically 48000)
 * @return 0 on success, negative on error
 */
int chirp_generator_init(uint32_t sample_rate);

/**
 * Play the log-swept sine through I2S to the speaker.
 * Blocks until playback is complete.
 *
 * @param sample_rate  Sample rate in Hz
 * @return 0 on success, negative on error
 */
int chirp_generator_play_sweep(uint32_t sample_rate);

/**
 * Get the precomputed inverse chirp buffer and its length.
 * Used by impulse_response.c for deconvolution.
 *
 * @param inv_chirp  Output pointer to inverse chirp float buffer
 * @param length     Output length in samples
 * @return 0 on success, negative on error
 */
int chirp_generator_get_inverse(float **inv_chirp, size_t *length);

/**
 * Generate a sustained sine at a specific frequency for room mode detection.
 * Plays for the specified duration, then stops.
 *
 * @param freq        Frequency in Hz
 * @param duration_ms Duration in milliseconds
 * @param sample_rate Sample rate in Hz
 * @return 0 on success, negative on error
 */
int chirp_generator_play_tone(float freq, uint32_t duration_ms, uint32_t sample_rate);

/**
 * Free all allocated chirp buffers.
 */
void chirp_generator_deinit(void);

#endif /* CHIRP_GENERATOR_H */