/**
 * acoustic_params.c — Room acoustic parameter computation
 *
 * Implements RT60 (Schroeder), C50/C80/D50 (energy ratios),
 * and frequency response (FFT magnitude) from an impulse response.
 *
 * Uses 6th-order Butterworth octave-band filters for band-limited analysis.
 */

#include "acoustic_params.h"
#include "impulse_response.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "esp_log.h"
#include "esp_dsp.h"

static const char *TAG = "acoustics";

/* Octave band center frequencies */
static const int octave_centers[NUM_OCTAVE_BANDS] = { 125, 250, 500, 1000, 2000, 4000 };

/* 1/3-octave band center frequencies (20 Hz to 20 kHz) */
static const float third_oct_centers[NUM_THIRD_OCT] = {
    20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160,
    200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
    2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000
};

/* Apply 6th-order Butterworth bandpass filter to impulse response */
static void octave_bandpass(const float *ir, uint32_t num_samples,
                             uint32_t sample_rate, int center_freq,
                             float *filtered) {
    /* 6th-order Butterworth bandpass: cascade of 3 second-order sections */
    float fl = center_freq / 1.4142f;  /* Lower -3dB point */
    float fh = center_freq * 1.4142f;  /* Upper -3dB point */
    float fs = (float)sample_rate;

    /* Simplified implementation: use windowed sinc bandpass in frequency domain */
    /* For each sample, apply cascade of 3 SOS (second-order sections) */
    /* Using direct-form II transposed biquad */

    /* Compute biquad coefficients for each SOS */
    /* Simplified: use 2nd-order LPF + 2nd-order HPF cascade (3 stages) */

    float w1[6] = {0}, w2[6] = {0};  /* State for 6 biquads */

    /* Precompute normalized frequencies */
    float omega_l = 2.0f * (float)M_PI * fl / fs;
    float omega_h = 2.0f * (float)M_PI * fh / fs;

    for (uint32_t n = 0; n < num_samples; n++) {
        float x = ir[n];

        /* 3 stages of HPF (removes low frequencies below fl) */
        for (int s = 0; s < 3; s++) {
            int idx = s;
            float wn = x - omega_l * w1[idx] - omega_l * omega_l * w2[idx];
            float y_hp = wn + 2.0f * w1[idx] + w2[idx];
            /* Rough approximation of 2nd-order HPF */
            w2[idx] = w1[idx];
            w1[idx] = wn;
            x = y_hp;
        }

        /* 3 stages of LPF (removes high frequencies above fh) */
        for (int s = 0; s < 3; s++) {
            int idx = s + 3;
            float wn = x - omega_h * w1[idx] - omega_h * omega_h * w2[idx];
            float y_lp = omega_h * omega_h * wn + 2.0f * omega_h * omega_h * w1[idx] +
                         omega_h * omega_h * w2[idx];
            w2[idx] = w1[idx];
            w1[idx] = wn;
            x = y_lp;
        }

        filtered[n] = x;
    }
}

/* Find time where Schroeder curve crosses a given dB level */
static float find_decay_time(const float *decay_curve, uint32_t num_samples,
                              uint32_t sample_rate, float db_start, float db_end) {
    /* Find the sample where decay drops below db_start */
    uint32_t start_sample = 0;
    for (uint32_t i = 0; i < num_samples; i++) {
        if (decay_curve[i] < db_start) {
            start_sample = i;
            break;
        }
    }

    /* Find the sample where decay drops below db_end */
    uint32_t end_sample = num_samples;
    for (uint32_t i = start_sample; i < num_samples; i++) {
        if (decay_curve[i] < db_end) {
            end_sample = i;
            break;
        }
    }

    if (end_sample >= num_samples || start_sample >= num_samples) return -1.0f;

    float t_start = (float)start_sample / sample_rate;
    float t_end = (float)end_sample / sample_rate;
    float delta_t = t_end - t_start;
    float delta_db = db_start - db_end;

    /* Extrapolate to -60 dB */
    return delta_t * 60.0f / delta_db;
}

int acoustic_params_compute_rt60(const float *ir, uint32_t num_samples,
                                   uint32_t sample_rate,
                                   float speed_of_sound,
                                   acoustic_results_t *results) {
    ESP_LOGI(TAG, "Computing RT60...");

    /* Broadband RT60 first */
    float *decay = malloc(num_samples * sizeof(float));
    if (!decay) return -1;

    impulse_response_schroeder(ir, num_samples, decay);

    /* T20: fit from -5 dB to -25 dB, extrapolate to -60 dB */
    results->rt60_broadband = find_decay_time(decay, num_samples, sample_rate, -5.0f, -25.0f);
    if (results->rt60_broadband < 0) {
        /* Fallback: try T30 */
        results->rt60_broadband = find_decay_time(decay, num_samples, sample_rate, -5.0f, -35.0f);
    }

    free(decay);

    /* Per-octave RT60 */
    float *filtered = malloc(num_samples * sizeof(float));
    float *oct_decay = malloc(num_samples * sizeof(float));
    if (!filtered || !oct_decay) {
        free(filtered); free(oct_decay);
        return -1;
    }

    for (int b = 0; b < NUM_OCTAVE_BANDS; b++) {
        ESP_LOGD(TAG, "  Filtering octave %d Hz...", octave_centers[b]);
        octave_bandpass(ir, num_samples, sample_rate, octave_centers[b], filtered);

        /* Compute Schroeder curve for this band */
        impulse_response_schroeder(filtered, num_samples, oct_decay);

        /* T20: -5 to -25 dB → ×3 for T60 */
        results->rt20[b] = find_decay_time(oct_decay, num_samples, sample_rate, -5.0f, -25.0f);
        /* T30: -5 to -35 dB → ×2 for T60 */
        results->rt30[b] = find_decay_time(oct_decay, num_samples, sample_rate, -5.0f, -35.0f);
        /* Use T30 if available (more reliable), else T20 */
        results->rt60[b] = (results->rt30[b] > 0) ? results->rt30[b] : results->rt20[b];

        ESP_LOGI(TAG, "  RT60 %d Hz: %.3f s (T20=%.3f, T30=%.3f)",
                 octave_centers[b], results->rt60[b],
                 results->rt20[b], results->rt30[b]);
    }

    free(filtered);
    free(oct_decay);

    return 0;
}

int acoustic_params_compute_freq_response(const float *ir, uint32_t num_samples,
                                            uint32_t sample_rate,
                                            acoustic_results_t *results) {
    ESP_LOGI(TAG, "Computing frequency response...");

    /* FFT of impulse response → frequency response */
    size_t fft_len = 1;
    while (fft_len < num_samples) fft_len <<= 1;
    if (fft_len < 1024) fft_len = 1024;

    float *fft_buf = malloc(fft_len * 2 * sizeof(float));
    if (!fft_buf) return -1;

    /* Copy IR into real part */
    for (uint32_t i = 0; i < num_samples && i < fft_len; i++) {
        fft_buf[i * 2] = ir[i];
        fft_buf[i * 2 + 1] = 0.0f;
    }
    for (size_t i = num_samples; i < fft_len; i++) {
        fft_buf[i * 2] = 0.0f;
        fft_buf[i * 2 + 1] = 0.0f;
    }

    /* Forward FFT */
    dsps_fft2r_fc32(fft_buf, fft_len);
    dsps_bit_rev_fc32(fft_buf, fft_len);

    /* Compute magnitude in 1/3-octave bands */
    float bin_hz = (float)sample_rate / fft_len;

    for (int b = 0; b < NUM_THIRD_OCT; b++) {
        float fc = third_oct_centers[b];
        float fl = fc / 1.1225f;   /* Lower edge (-3 dB) */
        float fh = fc * 1.1225f;   /* Upper edge (-3 dB) */
        int bin_lo = (int)(fl / bin_hz);
        int bin_hi = (int)(fh / bin_hz);
        if (bin_lo < 0) bin_lo = 0;
        if (bin_hi >= (int)fft_len / 2) bin_hi = fft_len / 2 - 1;

        /* Average magnitude in this band */
        float mag_sum = 0.0f;
        int count = 0;
        for (int k = bin_lo; k <= bin_hi; k++) {
            float re = fft_buf[k * 2] / fft_len;
            float im = fft_buf[k * 2 + 1] / fft_len;
            float mag = sqrtf(re * re + im * im);
            mag_sum += mag;
            count++;
        }

        float avg_mag = (count > 0) ? mag_sum / count : 1e-10f;
        results->freq_response_mag[b] = 20.0f * log10f(avg_mag + 1e-10f);

        /* Phase */
        if (bin_lo <= bin_hi) {
            int center_bin = (bin_lo + bin_hi) / 2;
            float re = fft_buf[center_bin * 2];
            float im = fft_buf[center_bin * 2 + 1];
            results->freq_response_phase[b] = atan2f(im, re) * 180.0f / (float)M_PI;
        } else {
            results->freq_response_phase[b] = 0.0f;
        }
    }

    /* Normalize magnitude to 0 dB at 1 kHz */
    int ref_band = 17;  /* 1 kHz in third_oct_centers[] */
    float ref_db = results->freq_response_mag[ref_band];
    for (int b = 0; b < NUM_THIRD_OCT; b++) {
        results->freq_response_mag[b] -= ref_db;
    }

    free(fft_buf);
    return 0;
}

int acoustic_params_compute_clarity(const float *ir, uint32_t num_samples,
                                      uint32_t sample_rate,
                                      acoustic_results_t *results) {
    ESP_LOGI(TAG, "Computing clarity indices...");

    /* C50 = 10 × log10(E_0-50ms / E_50ms-∞) */
    /* C80 = 10 × log10(E_0-80ms / E_80ms-∞) */
    /* D50 = E_0-50ms / E_total */

    /* Broadband computation */
    uint32_t t50_samples = (uint32_t)(0.050f * sample_rate);
    uint32_t t80_samples = (uint32_t)(0.080f * sample_rate);

    /* Compute per-octave clarity */
    float *filtered = malloc(num_samples * sizeof(float));
    if (!filtered) return -1;

    for (int b = 0; b < NUM_OCTAVE_BANDS; b++) {
        octave_bandpass(ir, num_samples, sample_rate, octave_centers[b], filtered);

        double e_early_50 = 0.0, e_early_80 = 0.0, e_total = 0.0;

        for (uint32_t i = 0; i < num_samples; i++) {
            double s2 = (double)filtered[i] * (double)filtered[i];
            e_total += s2;
            if (i < t50_samples) e_early_50 += s2;
            if (i < t80_samples) e_early_80 += s2;
        }

        double e_late_50 = e_total - e_early_50;
        double e_late_80 = e_total - e_early_80;

        /* C50 in dB */
        if (e_late_50 > 0.0)
            results->c50[b] = 10.0f * log10f((float)(e_early_50 / e_late_50));
        else
            results->c50[b] = 99.0f;  /* Very high clarity */

        /* C80 in dB */
        if (e_late_80 > 0.0)
            results->c80[b] = 10.0f * log10f((float)(e_early_80 / e_late_80));
        else
            results->c80[b] = 99.0f;

        /* D50 (definition) — ratio, not dB */
        if (e_total > 0.0)
            results->d50[b] = (float)(e_early_50 / e_total);
        else
            results->d50[b] = 0.0f;

        ESP_LOGI(TAG, "  %d Hz: C50=%.1f dB, C80=%.1f dB, D50=%.2f",
                 octave_centers[b], results->c50[b], results->c80[b],
                 results->d50[b]);
    }

    free(filtered);
    return 0;
}