/**
 * impulse_response.c — Overlap-save deconvolution for IR extraction
 *
 * The core DSP operation: given a captured room response to a swept sine,
 * and the precomputed inverse chirp filter, extract the impulse response
 * using overlap-save FFT convolution.
 *
 * The impulse response h(t) satisfies:
 *   captured(t) = chirp(t) * h(t)    (convolution)
 * So:
 *   h(t) = IFFT(FFT(captured) × FFT(inverse_chirp))
 *
 * For long signals, we use overlap-save with 32K-point FFTs.
 */

#include "impulse_response.h"
#include "chirp_generator.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "esp_log.h"
#include "esp_dsp.h"

static const char *TAG = "impulse";

/* FFT block size for overlap-save (must be power of 2) */
#define IR_FFT_SIZE  32768
#define IR_OVERLAP   (IR_FFT_SIZE / 2)  /* 50% overlap */

float *impulse_response_extract(const int16_t *captured, uint32_t num_samples,
                                 uint32_t sample_rate) {
    ESP_LOGI(TAG, "Extracting IR from %u samples...", num_samples);

    /* Get inverse chirp */
    float *inv_chirp = NULL;
    size_t inv_len = 0;
    if (chirp_generator_get_inverse(&inv_chirp, &inv_len) != 0) {
        ESP_LOGE(TAG, "Inverse chirp not available");
        return NULL;
    }

    /* Determine output length: keep 4 seconds of IR after the direct path peak */
    uint32_t ir_samples = sample_rate * 4;
    float *ir_output = malloc(ir_samples * sizeof(float));
    if (!ir_output) {
        ESP_LOGE(TAG, "IR output buffer alloc failed");
        return NULL;
    }
    memset(ir_output, 0, ir_samples * sizeof(float));

    /* Convert captured int16 to float */
    float *captured_f = malloc(num_samples * sizeof(float));
    if (!captured_f) {
        free(ir_output);
        return NULL;
    }
    for (uint32_t i = 0; i < num_samples; i++) {
        captured_f[i] = (float)captured[i] / 32768.0f;
    }

    /* Allocate FFT work buffers */
    float *fft_a = malloc(IR_FFT_SIZE * 2 * sizeof(float));  /* Complex */
    float *fft_b = malloc(IR_FFT_SIZE * 2 * sizeof(float));  /* Complex */
    float *fft_out = malloc(IR_FFT_SIZE * 2 * sizeof(float));
    if (!fft_a || !fft_b || !fft_out) {
        ESP_LOGE(TAG, "FFT buffer alloc failed");
        free(ir_output); free(captured_f);
        free(fft_a); free(fft_b); free(fft_out);
        return NULL;
    }

    /* Precompute FFT of inverse chirp (zero-padded to IR_FFT_SIZE) */
    memset(fft_b, 0, IR_FFT_SIZE * 2 * sizeof(float));
    size_t chirp_pad = (inv_len < IR_FFT_SIZE) ? inv_len : IR_FFT_SIZE;
    for (size_t i = 0; i < chirp_pad; i++) {
        fft_b[i * 2] = inv_chirp[i];       /* Real */
        fft_b[i * 2 + 1] = 0.0f;           /* Imaginary */
    }
    dsps_fft2r_fc32(fft_b, IR_FFT_SIZE);
    dsps_bit_rev_fc32(fft_b, IR_FFT_SIZE);

    /* Overlap-save convolution */
    uint32_t hop = IR_FFT_SIZE - IR_OVERLAP;  /* Valid samples per block */
    uint32_t out_idx = 0;

    for (uint32_t block_start = 0; block_start < num_samples && out_idx < ir_samples;
         block_start += hop) {

        /* Prepare input block with overlap */
        memset(fft_a, 0, IR_FFT_SIZE * 2 * sizeof(float));

        uint32_t start = (block_start > IR_OVERLAP) ? block_start - IR_OVERLAP : 0;
        uint32_t avail = num_samples - start;
        uint32_t to_copy = (avail < IR_FFT_SIZE) ? avail : IR_FFT_SIZE;

        for (uint32_t i = 0; i < to_copy; i++) {
            fft_a[i * 2] = captured_f[start + i];
            fft_a[i * 2 + 1] = 0.0f;
        }

        /* Forward FFT */
        dsps_fft2r_fc32(fft_a, IR_FFT_SIZE);
        dsps_bit_rev_fc32(fft_a, IR_FFT_SIZE);

        /* Complex multiply: fft_out = fft_a × fft_b */
        for (int i = 0; i < IR_FFT_SIZE; i++) {
            float ar = fft_a[i * 2],     ai = fft_a[i * 2 + 1];
            float br = fft_b[i * 2],     bi = fft_b[i * 2 + 1];
            fft_out[i * 2]     = ar * br - ai * bi;
            fft_out[i * 2 + 1] = ar * bi + ai * br;
        }

        /* Inverse FFT */
        dsps_fft2r_fc32(fft_out, IR_FFT_SIZE);
        dsps_bit_rev_fc32(fft_out, IR_FFT_SIZE);

        /* Extract valid samples (skip overlap region) and scale */
        uint32_t valid_start = IR_OVERLAP;
        for (uint32_t i = valid_start; i < IR_FFT_SIZE && out_idx < ir_samples; i++) {
            ir_output[out_idx++] = fft_out[i * 2] / IR_FFT_SIZE;
        }
    }

    /* Find the peak of the IR (direct path) and align */
    float max_val = 0.0f;
    uint32_t peak_idx = 0;
    for (uint32_t i = 0; i < ir_samples && i < out_idx; i++) {
        float abs_val = fabsf(ir_output[i]);
        if (abs_val > max_val) {
            max_val = abs_val;
            peak_idx = i;
        }
    }

    /* Shift IR so peak is at sample 0 (remove system delay) */
    if (peak_idx > 0 && peak_idx < ir_samples / 2) {
        memmove(ir_output, ir_output + peak_idx,
                (ir_samples - peak_idx) * sizeof(float));
        memset(ir_output + (ir_samples - peak_idx), 0, peak_idx * sizeof(float));
        ESP_LOGI(TAG, "IR peak at sample %u, aligned to 0", peak_idx);
    }

    /* Normalize IR peak to 1.0 */
    if (max_val > 0.0f) {
        for (uint32_t i = 0; i < ir_samples; i++) {
            ir_output[i] /= max_val;
        }
    }

    free(captured_f);
    free(fft_a);
    free(fft_b);
    free(fft_out);

    ESP_LOGI(TAG, "IR extracted: %u samples (%.1f s)", ir_samples,
             (float)ir_samples / sample_rate);
    return ir_output;
}

int impulse_response_schroeder(const float *ir, uint32_t num_samples,
                                float *decay_curve) {
    if (!ir || !decay_curve) return -1;

    /* Compute total energy */
    double total_energy = 0.0;
    for (uint32_t i = 0; i < num_samples; i++) {
        total_energy += (double)ir[i] * (double)ir[i];
    }

    if (total_energy < 1e-20) {
        memset(decay_curve, 0, num_samples * sizeof(float));
        return -1;
    }

    /* Backward integration: E(t) = ∫t^∞ h²(τ)dτ / total_energy */
    double running = total_energy;
    for (uint32_t i = 0; i < num_samples; i++) {
        decay_curve[i] = 10.0f * log10f((float)(running / total_energy));
        running -= (double)ir[i] * (double)ir[i];
        if (running < 0.0) running = 0.0;
    }

    return 0;
}