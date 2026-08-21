/*
 * Tremor Tile — FFT Engine Header
 * fft_engine.h — Data structures and function prototypes
 */

#ifndef TREMOR_TILE_FFT_ENGINE_H
#define TREMOR_TILE_FFT_ENGINE_H

#include <stdint.h>
#include <stdbool.h>
#include "sensor_acq.h"

// FFT axis selection
#define FFT_AXIS_X    0
#define FFT_AXIS_Y    1
#define FFT_AXIS_Z    2

// Sample buffer for FFT accumulation
typedef struct {
    float data[FFT_SIZE];  // Window of samples (one axis)
    uint16_t count;        // Current number of samples
    uint8_t axis;          // Which axis (FFT_AXIS_X/Y/Z)
} sample_buffer_t;

// Spectral features extracted from FFT
typedef struct {
    // Peak frequencies and amplitudes
    float peak_freqs[NUM_PEAK_FREQUENCIES];      // Hz
    float peak_amplitudes[NUM_PEAK_FREQUENCIES];  // g/√Hz
    uint8_t num_peaks;

    // Band energies (integrated PSD in each band)
    float band_energies[NUM_FREQ_BANDS];  // g²·Hz

    // Time-domain features
    float rms;           // Root-mean-square vibration (g)
    float crest_factor;  // Peak / RMS
    float kurtosis;      // 4th moment normalized (impulsiveness)

    // Metadata
    int64_t timestamp;    // Unix timestamp
    uint16_t fft_size;    // Number of FFT points
    float sample_rate;    // Hz
    float freq_resolution; // Hz per bin
} spectral_features_t;

// Initialize FFT engine (precompute window, init CMSIS-DSP)
void fft_engine_init(void);

// Reset sample buffer
void fft_engine_reset_buffer(sample_buffer_t *buf);

// Append a batch of samples to the rolling buffer
void fft_engine_append(sample_buffer_t *buf, sample_batch_t *batch);

// Reset buffer with overlap (keep second half)
void fft_engine_overlap_reset(sample_buffer_t *buf);

// Compute FFT and extract features
void fft_engine_compute(sample_buffer_t *buf, spectral_features_t *features);

// Compute noise floor (median of magnitude spectrum)
float compute_noise_floor(float *magnitude, uint16_t num_bins);

// Find top N peak frequencies
void find_peak_frequencies(float *magnitude, uint16_t num_bins,
                           float freq_resolution, float noise_floor,
                           spectral_features_t *features);

// Compute energy in predefined frequency bands
void compute_band_energies(float *magnitude, uint16_t num_bins,
                           float freq_resolution, spectral_features_t *features);

// Compute spectral centroid
float fft_engine_spectral_centroid(spectral_features_t *features);

// Compute total spectral energy
float fft_engine_total_energy(spectral_features_t *features);

#endif // TREMOR_TILE_FFT_ENGINE_H