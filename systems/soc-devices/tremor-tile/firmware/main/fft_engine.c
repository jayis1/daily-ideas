/*
 * Tremor Tile — FFT Engine
 * fft_engine.c — 1024-point FFT, spectral feature extraction, windowing
 *
 * Uses ARM CMSIS-DSP library for FFT computation on RP2040
 * Processes vibration data from inter-core FIFO
 */

#include "fft_engine.h"
#include "config.h"
#include <math.h>
#include <string.h>
#include <stdio.h>

// CMSIS-DSP include (Pico SDK compatible)
#include "arm_math.h"

// Hann window coefficients (precomputed for FFT_SIZE=1024)
static float hann_window[FFT_SIZE];
static bool window_initialized = false;

// FFT working buffers
static float fft_input[FFT_SIZE * 2];   // Complex input (real, imag interleaved)
static float fft_output[FFT_SIZE * 2];  // Complex output
static float fft_magnitude[FFT_SIZE];   // Magnitude spectrum
static arm_cfft_instance_f32 fft_instance;

// Initialize FFT engine
void fft_engine_init(void) {
    // Initialize CMSIS-DSP FFT instance
    arm_status status = arm_cfft_init_f32(&fft_instance, FFT_SIZE);
    if (status != ARM_MATH_SUCCESS) {
        printf("FFT: Initialization failed! status=%d\n", status);
        return;
    }

    // Precompute Hann window
    // w(n) = 0.5 * (1 - cos(2πn / (N-1)))
    for (int i = 0; i < FFT_SIZE; i++) {
        hann_window[i] = 0.5f * (1.0f - cosf(2.0f * M_PI * (float)i / (float)(FFT_SIZE - 1)));
    }
    window_initialized = true;

    printf("FFT: Initialized — %d-point FFT, Hann window\n", FFT_SIZE);
}

// Reset sample buffer
void fft_engine_reset_buffer(sample_buffer_t *buf) {
    buf->count = 0;
    buf->axis = FFT_AXIS_Z;  // Default: Z-axis (vertical vibration)
}

// Append a batch of samples to the rolling buffer
// We extract one axis at a time for FFT
void fft_engine_append(sample_buffer_t *buf, sample_batch_t *batch) {
    for (uint16_t i = 0; i < batch->count && buf->count < FFT_SIZE; i++) {
        float value;
        switch (buf->axis) {
            case FFT_AXIS_X: value = batch->samples[i].x; break;
            case FFT_AXIS_Y: value = batch->samples[i].y; break;
            case FFT_AXIS_Z: value = batch->samples[i].z; break;
            default: value = batch->samples[i].z; break;
        }
        buf->data[buf->count++] = value;
    }
}

// Reset buffer with 50% overlap (keep second half of current data)
void fft_engine_overlap_reset(sample_buffer_t *buf) {
    uint16_t overlap_start = FFT_SIZE / 2;
    uint16_t overlap_count = FFT_SIZE - overlap_start;

    // Shift second half to beginning
    memmove(buf->data, &buf->data[overlap_start], overlap_count * sizeof(float));
    buf->count = overlap_count;
}

// Compute FFT and extract spectral features
void fft_engine_compute(sample_buffer_t *buf, spectral_features_t *features) {
    if (buf->count < FFT_SIZE || !window_initialized) {
        return;
    }

    // 1. Apply window function and fill complex input buffer
    for (int i = 0; i < FFT_SIZE; i++) {
        float windowed = buf->data[i] * hann_window[i];
        fft_input[2 * i] = windowed;       // Real part
        fft_input[2 * i + 1] = 0.0f;       // Imaginary part
    }

    // 2. Compute FFT (in-place)
    arm_cfft_f32(&fft_instance, fft_input, 0, 1);  // Forward FFT, bit reversal

    // 3. Compute magnitude spectrum
    // Only need first FFT_SIZE/2 bins (Nyquist)
    for (int i = 0; i < FFT_SIZE / 2; i++) {
        float real = fft_input[2 * i];
        float imag = fft_input[2 * i + 1];
        fft_magnitude[i] = sqrtf(real * real + imag * imag);
    }

    // 4. Compute frequency resolution
    float freq_resolution = (float)ADXL355_ODR / (float)FFT_SIZE;  // Hz per bin

    // 5. Extract features
    memset(features, 0, sizeof(spectral_features_t));

    // --- RMS vibration ---
    float sum_sq = 0.0f;
    for (uint16_t i = 0; i < buf->count; i++) {
        sum_sq += buf->data[i] * buf->data[i];
    }
    features->rms = sqrtf(sum_sq / (float)buf->count);

    // --- Peak frequency detection ---
    // Find top 5 peaks above noise floor
    float noise_floor = compute_noise_floor(fft_magnitude, FFT_SIZE / 2);
    find_peak_frequencies(fft_magnitude, FFT_SIZE / 2, freq_resolution,
                          noise_floor, features);

    // --- Band energy ---
    compute_band_energies(fft_magnitude, FFT_SIZE / 2, freq_resolution, features);

    // --- Crest factor (peak / RMS) ---
    float peak_val = 0.0f;
    for (uint16_t i = 0; i < buf->count; i++) {
        float abs_val = fabsf(buf->data[i]);
        if (abs_val > peak_val) peak_val = abs_val;
    }
    features->crest_factor = (features->rms > 0.0f) ? (peak_val / features->rms) : 0.0f;

    // --- Kurtosis (4th moment) ---
    // κ = (1/N) Σ((x - μ)⁴) / σ⁴ - 3
    float mean = 0.0f;
    for (uint16_t i = 0; i < buf->count; i++) {
        mean += buf->data[i];
    }
    mean /= (float)buf->count;

    float variance = 0.0f;
    float fourth_moment = 0.0f;
    for (uint16_t i = 0; i < buf->count; i++) {
        float diff = buf->data[i] - mean;
        variance += diff * diff;
        fourth_moment += diff * diff * diff * diff;
    }
    variance /= (float)buf->count;
    fourth_moment /= (float)buf->count;

    if (variance > 1e-12f) {
        features->kurtosis = (fourth_moment / (variance * variance)) - 3.0f;
    } else {
        features->kurtosis = 0.0f;
    }

    // Store metadata
    features->timestamp = 0;  // Will be set by caller
    features->fft_size = FFT_SIZE;
    features->sample_rate = ADXL355_ODR;
    features->freq_resolution = freq_resolution;
}

// Compute noise floor as median of magnitude spectrum
float compute_noise_floor(float *magnitude, uint16_t num_bins) {
    // Simple median estimate: sort a subset and take middle value
    // For efficiency, use the 75th percentile as a noise floor estimate
    float sum = 0.0f;
    for (uint16_t i = 1; i < num_bins; i++) {  // Skip DC bin
        sum += magnitude[i];
    }
    return sum / (float)(num_bins - 1) * 0.5f;  // Conservative noise floor
}

// Find top N peak frequencies above noise floor
void find_peak_frequencies(float *magnitude, uint16_t num_bins,
                           float freq_resolution, float noise_floor,
                           spectral_features_t *features) {
    float threshold = noise_floor * 3.0f;  // 3x noise floor minimum

    // Simple peak detection: higher than both neighbors and above threshold
    typedef struct { float freq; float amplitude; } peak_t;
    peak_t peaks[NUM_PEAK_FREQUENCIES];
    int num_peaks = 0;

    for (uint16_t i = 2; i < num_bins - 2 && num_peaks < NUM_PEAK_FREQUENCIES; i++) {
        if (magnitude[i] > magnitude[i-1] &&
            magnitude[i] > magnitude[i+1] &&
            magnitude[i] > threshold) {
            // This is a peak
            peaks[num_peaks].freq = (float)i * freq_resolution;
            peaks[num_peaks].amplitude = magnitude[i];
            num_peaks++;
        }
    }

    // Sort peaks by amplitude (descending) using simple insertion sort
    for (int i = 1; i < num_peaks; i++) {
        peak_t key = peaks[i];
        int j = i - 1;
        while (j >= 0 && peaks[j].amplitude < key.amplitude) {
            peaks[j + 1] = peaks[j];
            j--;
        }
        peaks[j + 1] = key;
    }

    // Copy to features
    for (int i = 0; i < NUM_PEAK_FREQUENCIES; i++) {
        if (i < num_peaks) {
            features->peak_freqs[i] = peaks[i].freq;
            features->peak_amplitudes[i] = peaks[i].amplitude;
        } else {
            features->peak_freqs[i] = 0.0f;
            features->peak_amplitudes[i] = 0.0f;
        }
    }
    features->num_peaks = num_peaks;
}

// Compute energy in predefined frequency bands
void compute_band_energies(float *magnitude, uint16_t num_bins,
                           float freq_resolution, spectral_features_t *features) {
    // Band definitions: {min_freq, max_freq}
    float bands[NUM_FREQ_BANDS][2] = {
        {BAND_VERY_LOW_MIN, BAND_VERY_LOW_MAX},    // 0.1 – 10 Hz
        {BAND_LOW_MIN, BAND_LOW_MAX},               // 10 – 50 Hz
        {BAND_MID_MIN, BAND_MID_MAX},               // 50 – 200 Hz
        {BAND_HIGH_MIN, BAND_HIGH_MAX},             // 200 – 500 Hz
        {BAND_VERY_HIGH_MIN, BAND_VERY_HIGH_MAX},   // 500 – 1500 Hz
    };

    for (int b = 0; b < NUM_FREQ_BANDS; b++) {
        float energy = 0.0f;
        uint16_t start_bin = (uint16_t)(bands[b][0] / freq_resolution);
        uint16_t end_bin = (uint16_t)(bands[b][1] / freq_resolution);

        if (end_bin >= num_bins) end_bin = num_bins - 1;
        if (start_bin < 1) start_bin = 1;  // Skip DC

        for (uint16_t i = start_bin; i <= end_bin; i++) {
            energy += magnitude[i] * magnitude[i];
        }

        features->band_energies[b] = energy;
    }
}

// Compute spectral centroid (weighted average frequency)
float fft_engine_spectral_centroid(spectral_features_t *features) {
    float weighted_sum = 0.0f;
    float total_weight = 0.0f;

    for (int i = 0; i < features->num_peaks; i++) {
        weighted_sum += features->peak_freqs[i] * features->peak_amplitudes[i];
        total_weight += features->peak_amplitudes[i];
    }

    return (total_weight > 0.0f) ? (weighted_sum / total_weight) : 0.0f;
}

// Compute total spectral energy
float fft_engine_total_energy(spectral_features_t *features) {
    float total = 0.0f;
    for (int i = 0; i < NUM_FREQ_BANDS; i++) {
        total += features->band_energies[i];
    }
    return total;
}