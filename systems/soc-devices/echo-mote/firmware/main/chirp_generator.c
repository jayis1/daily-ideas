/**
 * chirp_generator.c — Logarithmic swept-sine synthesis and inverse chirp
 *
 * A log-swept sine (exponential chirp) sweeps from fmin to fmax over
 * a given duration. The inverse chirp is the time-reversed and amplitude-
 * modulated version used for impulse response deconvolution:
 *
 *   inverse_chirp(t) = chirp(T - t) * envelope(T - t) / |FFT(chirp)|²
 *
 * For a perfect deconvolution, we divide in the frequency domain.
 * In practice we precompute the inverse filter as:
 *   inv_filter = IFFT(1 / FFT(chirp))
 * and apply it via overlap-save convolution.
 */

#include "chirp_generator.h"
#include "i2s_manager.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "esp_log.h"
#include "esp_dsp.h"

static const char *TAG = "chirp_gen";

/* Precomputed buffers (allocated in PSRAM) */
static float *forward_chirp = NULL;    /* Forward log-swept sine */
static float *inverse_chirp = NULL;    /* Inverse filter for deconvolution */
static size_t chirp_length = 0;       /* Length in samples */
static uint32_t init_sample_rate = 0;

/* Log-swept sine: instantaneous frequency increases exponentially */
static void generate_log_chirp(float *buf, size_t len,
                                float fmin, float fmax,
                                uint32_t sample_rate) {
    float T = (float)len / sample_rate;
    float ratio = fmax / fmin;

    for (size_t i = 0; i < len; i++) {
        float t = (float)i / sample_rate;
        /* Instantaneous phase: integral of 2π × fmin × ratio^(t/T) dt */
        float phase = 2.0f * (float)M_PI * fmin * T / logf(ratio) *
                      (powf(ratio, t / T) - 1.0f);
        buf[i] = sinf(phase);

        /* Apply fade-in (first 50 ms) and fade-out (last 20 ms) */
        float fade_in_samples = sample_rate * 0.05f;   /* 50 ms */
        float fade_out_samples = sample_rate * 0.02f;   /* 20 ms */
        if (i < (size_t)fade_in_samples) {
            buf[i] *= (float)i / fade_in_samples;
        }
        if (i > len - (size_t)fade_out_samples) {
            buf[i] *= (float)(len - i) / fade_out_samples;
        }
    }
}

/* Compute inverse filter in frequency domain */
static void compute_inverse_filter(const float *forward, float *inv,
                                     size_t len) {
    /*
     * Inverse filter: IFFT(1 / FFT(forward_chirp))
     * We use ESP-DSP FFT routines.
     * The forward chirp's spectrum magnitude is |X(f)|,
     * so the inverse filter's spectrum is 1/|X(f)| with conjugate phase.
     *
     * For a log sweep, the spectral magnitude rolls off at ~3 dB/octave
     * (pink-ish spectrum). The inverse filter compensates this,
     * making the effective excitation white.
     */

    /* Allocate complex FFT buffers (real + imaginary interleaved) */
    size_t fft_len = 1;
    while (fft_len < len) fft_len <<= 1;  /* Next power of 2 */

    float *fft_buf = calloc(fft_len * 2, sizeof(float));  /* Complex */
    float *inv_fft = calloc(fft_len * 2, sizeof(float));

    if (!fft_buf || !inv_fft) {
        ESP_LOGE(TAG, "FFT buffer allocation failed");
        free(fft_buf); free(inv_fft);
        return;
    }

    /* Copy forward chirp into real part, zero imaginary */
    for (size_t i = 0; i < len; i++) {
        fft_buf[i * 2] = forward[i];
        fft_buf[i * 2 + 1] = 0.0f;
    }
    for (size_t i = len; i < fft_len; i++) {
        fft_buf[i * 2] = 0.0f;
        fft_buf[i * 2 + 1] = 0.0f;
    }

    /* Forward FFT */
    dsps_fft2r_fc32(fft_buf, fft_len);
    dsps_bit_rev_fc32(fft_buf, fft_len);

    /* Compute 1/X(f) with regularization to avoid division by zero */
    float eps = 1e-6f;
    for (size_t i = 0; i < fft_len; i++) {
        float re = fft_buf[i * 2];
        float im = fft_buf[i * 2 + 1];
        float mag_sq = re * re + im * im;
        if (mag_sq < eps) mag_sq = eps;

        /* Conjugate and divide by magnitude squared */
        inv_fft[i * 2] = re / mag_sq;
        inv_fft[i * 2 + 1] = -im / mag_sq;
    }

    /* Inverse FFT */
    dsps_fft2r_fc32(inv_fft, fft_len);
    dsps_bit_rev_fc32(inv_fft, fft_len);

    /* Scale by 1/N */
    for (size_t i = 0; i < fft_len; i++) {
        inv_fft[i * 2] /= fft_len;
        inv_fft[i * 2 + 1] /= fft_len;
    }

    /* Time-reverse to get the proper inverse filter */
    for (size_t i = 0; i < len; i++) {
        inv[i] = inv_fft[(len - 1 - i) * 2];  /* Real part only */
    }

    free(fft_buf);
    free(inv_fft);
}

int chirp_generator_init(uint32_t sample_rate) {
    init_sample_rate = sample_rate;
    chirp_length = (size_t)(CHIRP_DURATION_S * sample_rate);

    ESP_LOGI(TAG, "Initializing chirp: %d samples (%.1f s at %d Hz)",
             (int)chirp_length, CHIRP_DURATION_S, sample_rate);

    /* Allocate in PSRAM (these are large buffers) */
    forward_chirp = malloc(chirp_length * sizeof(float));
    inverse_chirp = malloc(chirp_length * sizeof(float));

    if (!forward_chirp || !inverse_chirp) {
        ESP_LOGE(TAG, "Chirp buffer allocation failed (need %.1f KB each)",
                 chirp_length * sizeof(float) / 1024.0f);
        free(forward_chirp); free(inverse_chirp);
        return -1;
    }

    /* Generate forward log-swept sine */
    generate_log_chirp(forward_chirp, chirp_length,
                        CHIRP_FMIN_HZ, CHIRP_FMAX_HZ, sample_rate);

    /* Compute inverse filter */
    compute_inverse_filter(forward_chirp, inverse_chirp, chirp_length);

    ESP_LOGI(TAG, "Chirp and inverse filter ready (%.1f KB each)",
             chirp_length * sizeof(float) / 1024.0f);

    return 0;
}

int chirp_generator_play_sweep(uint32_t sample_rate) {
    if (!forward_chirp || sample_rate != init_sample_rate) {
        ESP_LOGE(TAG, "Chirp not initialized for sample rate %u", sample_rate);
        return -1;
    }

    ESP_LOGI(TAG, "Playing swept sine: %.0f–%.0f Hz over %.1f s",
             CHIRP_FMIN_HZ, CHIRP_FMAX_HZ, CHIRP_DURATION_S);

    /* Convert float chirp to int16 and write to I2S TX */
    int16_t *pcm_buf = malloc(chirp_length * sizeof(int16_t));
    if (!pcm_buf) return -1;

    for (size_t i = 0; i < chirp_length; i++) {
        /* Scale to ~75 dB SPL at 1m (approx -12 dBFS) */
        float sample = forward_chirp[i] * 0.25f;
        if (sample > 1.0f) sample = 1.0f;
        if (sample < -1.0f) sample = -1.0f;
        pcm_buf[i] = (int16_t)(sample * 32767.0f);
    }

    /* Write to I2S in chunks */
    size_t offset = 0;
    size_t chunk = 1024;
    while (offset < chirp_length) {
        size_t to_write = (chirp_length - offset > chunk) ?
                          chunk : (chirp_length - offset);
        i2s_manager_write_speaker((const uint8_t *)(pcm_buf + offset),
                                   to_write * sizeof(int16_t));
        offset += to_write;
    }

    free(pcm_buf);
    return 0;
}

int chirp_generator_get_inverse(float **inv_chirp, size_t *length) {
    if (!inverse_chirp) return -1;
    *inv_chirp = inverse_chirp;
    *length = chirp_length;
    return 0;
}

int chirp_generator_play_tone(float freq, uint32_t duration_ms,
                               uint32_t sample_rate) {
    size_t num_samples = (size_t)(sample_rate * duration_ms / 1000);
    int16_t *pcm_buf = malloc(num_samples * sizeof(int16_t));
    if (!pcm_buf) return -1;

    float omega = 2.0f * (float)M_PI * freq / sample_rate;
    float phase = 0.0f;
    float fade_samples = sample_rate * 0.01f;  /* 10 ms fade */

    for (size_t i = 0; i < num_samples; i++) {
        float sample = sinf(phase) * 0.25f;  /* -12 dBFS */

        /* Fade in/out */
        if (i < (size_t)fade_samples)
            sample *= (float)i / fade_samples;
        if (i > num_samples - (size_t)fade_samples)
            sample *= (float)(num_samples - i) / fade_samples;

        pcm_buf[i] = (int16_t)(sample * 32767.0f);
        phase += omega;
        if (phase > 2.0f * (float)M_PI) phase -= 2.0f * (float)M_PI;
    }

    /* Write to I2S */
    size_t offset = 0;
    size_t chunk = 1024;
    while (offset < num_samples) {
        size_t to_write = (num_samples - offset > chunk) ?
                          chunk : (num_samples - offset);
        i2s_manager_write_speaker((const uint8_t *)(pcm_buf + offset),
                                   to_write * sizeof(int16_t));
        offset += to_write;
    }

    free(pcm_buf);
    return 0;
}

void chirp_generator_deinit(void) {
    free(forward_chirp);
    free(inverse_chirp);
    forward_chirp = NULL;
    inverse_chirp = NULL;
    chirp_length = 0;
}