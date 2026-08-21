/**
 * room_modes.c — Room mode detection and classification
 *
 * Two-phase approach:
 * 1. "Ping and listen": play brief tones at each frequency 20–300 Hz,
 *    measure decay time after each. Frequencies with abnormally long
 *    decay are candidate room modes.
 * 2. "IR spectral analysis": examine the low-frequency spectrum of
 *    the swept-sine impulse response for peaks above the noise floor.
 *
 * Room modes are classified as:
 *   Axial (between 2 parallel walls) — strongest
 *   Tangential (4 walls + floor/ceiling) — moderate
 *   Oblique (all 6 surfaces) — weakest
 *
 * Classification is done by harmonic relationships: if a mode frequency
 * is approximately an integer multiple of a lower mode, it's likely
 * a higher-order axial mode. Otherwise, tangential or oblique.
 */

#include "room_modes.h"
#include "chirp_generator.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "esp_log.h"
#include "esp_dsp.h"

static const char *TAG = "room_modes";

/* Room mode scan parameters */
#define MODE_FMIN       20      /* Hz */
#define MODE_FMAX       300     /* Hz */
#define MODE_STEP       1       /* Hz */
#define MODE_PING_MS    50      /* Ping duration in ms */
#define MODE_GAP_MS     20      /* Gap between pings in ms */

int room_modes_play_pings(uint32_t sample_rate) {
    ESP_LOGI(TAG, "Playing room mode pings: %d–%d Hz, step %d Hz",
             MODE_FMIN, MODE_FMAX, MODE_STEP);

    for (int freq = MODE_FMIN; freq <= MODE_FMAX; freq += MODE_STEP) {
        chirp_generator_play_tone((float)freq, MODE_PING_MS, sample_rate);
        /* Gap for decay measurement */
        vTaskDelay(pdMS_TO_TICKS(MODE_GAP_MS));
    }

    ESP_LOGI(TAG, "Room mode ping sequence complete");
    return 0;
}

/* Measure decay time from a portion of the captured signal */
static float measure_decay_time(const int16_t *samples, uint32_t num_samples,
                                  uint32_t sample_rate) {
    /* Find the peak */
    int16_t peak_val = 0;
    uint32_t peak_idx = 0;
    for (uint32_t i = 0; i < num_samples; i++) {
        int16_t abs_val = (samples[i] >= 0) ? samples[i] : -samples[i];
        if (abs_val > peak_val) {
            peak_val = abs_val;
            peak_idx = i;
        }
    }

    if (peak_val < 100) return 0.0f;  /* Below noise floor */

    /* Find time for signal to decay to -20 dB below peak */
    int16_t threshold = peak_val / 10;  /* -20 dB ≈ 1/10 */
    uint32_t decay_end = num_samples;
    for (uint32_t i = peak_idx; i < num_samples; i++) {
        int16_t abs_val = (samples[i] >= 0) ? samples[i] : -samples[i];
        if (abs_val < threshold) {
            decay_end = i;
            break;
        }
    }

    float decay_time = (float)(decay_end - peak_idx) / sample_rate;
    return decay_time;
}

int room_modes_analyze(const float *ir, uint32_t num_samples,
                        uint32_t sample_rate, float speed_of_sound,
                        acoustic_results_t *results) {
    ESP_LOGI(TAG, "Analyzing room modes from IR...");

    results->num_modes = 0;

    /* Method: FFT of IR, find peaks in 20-300 Hz range */
    size_t fft_len = 1;
    while (fft_len < num_samples) fft_len <<= 1;

    float *fft_buf = malloc(fft_len * 2 * sizeof(float));
    if (!fft_buf) return -1;

    /* Zero-pad and compute FFT */
    for (uint32_t i = 0; i < num_samples && i < fft_len; i++) {
        fft_buf[i * 2] = ir[i];
        fft_buf[i * 2 + 1] = 0.0f;
    }
    for (size_t i = num_samples; i < fft_len; i++) {
        fft_buf[i * 2] = 0.0f;
        fft_buf[i * 2 + 1] = 0.0f;
    }

    dsps_fft2r_fc32(fft_buf, fft_len);
    dsps_bit_rev_fc32(fft_buf, fft_len);

    float bin_hz = (float)sample_rate / fft_len;

    /* Compute magnitude spectrum in 20-300 Hz range */
    int bin_lo = (int)(20.0f / bin_hz);
    int bin_hi = (int)(300.0f / bin_hz);

    /* Find average magnitude (noise floor estimate) */
    double avg_mag = 0.0;
    int count = 0;
    for (int k = bin_lo; k <= bin_hi; k++) {
        float re = fft_buf[k * 2] / fft_len;
        float im = fft_buf[k * 2 + 1] / fft_len;
        float mag = sqrtf(re * re + im * im);
        avg_mag += mag;
        count++;
    }
    avg_mag /= count;

    /* Threshold: 10× average (20 dB above noise floor) */
    float threshold = avg_mag * 10.0f;

    /* Find peaks: local maxima above threshold */
    for (int k = bin_lo + 1; k < bin_hi && results->num_modes < MAX_ROOM_MODES; k++) {
        float re_curr = fft_buf[k * 2] / fft_len;
        float im_curr = fft_buf[k * 2 + 1] / fft_len;
        float mag_curr = sqrtf(re_curr * re_curr + im_curr * im_curr);

        float re_prev = fft_buf[(k - 1) * 2] / fft_len;
        float im_prev = fft_buf[(k - 1) * 2 + 1] / fft_len;
        float mag_prev = sqrtf(re_prev * re_prev + im_prev * im_prev);

        float re_next = fft_buf[(k + 1) * 2] / fft_len;
        float im_next = fft_buf[(k + 1) * 2 + 1] / fft_len;
        float mag_next = sqrtf(re_next * re_next + im_next * im_next);

        /* Local maximum above threshold */
        if (mag_curr > threshold && mag_curr > mag_prev && mag_curr > mag_next) {
            float freq = k * bin_hz;
            int idx = results->num_modes;

            results->room_modes[idx].freq = freq;

            /* Estimate decay time from bandwidth (Q factor) */
            /* 3 dB bandwidth ≈ f / Q, decay time ≈ Q / (π × f) */
            float half_power = mag_curr * 0.707f;
            int lo_edge = k, hi_edge = k;
            while (lo_edge > bin_lo) {
                float re = fft_buf[lo_edge * 2] / fft_len;
                float im = fft_buf[lo_edge * 2 + 1] / fft_len;
                if (sqrtf(re * re + im * im) < half_power) break;
                lo_edge--;
            }
            while (hi_edge < bin_hi) {
                float re = fft_buf[hi_edge * 2] / fft_len;
                float im = fft_buf[hi_edge * 2 + 1] / fft_len;
                if (sqrtf(re * re + im * im) < half_power) break;
                hi_edge++;
            }
            float bw = (hi_edge - lo_edge) * bin_hz;
            if (bw > 0.5f) {
                float q = freq / bw;
                results->room_modes[idx].decay_time = q / ((float)M_PI * freq);
            } else {
                results->room_modes[idx].decay_time = 1.0f;
            }

            /* Classify mode type by harmonic relationship with lower modes */
            results->room_modes[idx].type = 0;  /* Default: axial */
            for (int m = 0; m < idx; m++) {
                float ratio = freq / results->room_modes[m].freq;
                float nearest_int = roundf(ratio);
                if (fabsf(ratio - nearest_int) < 0.05f && nearest_int > 1.0f) {
                    /* Harmonic relationship: likely higher-order axial */
                    results->room_modes[idx].type = 0;
                    break;
                }
            }
            /* If no harmonic relationship found, classify as tangential */
            if (results->room_modes[idx].type == 0 && idx > 0) {
                bool harmonic_found = false;
                for (int m = 0; m < idx; m++) {
                    float ratio = freq / results->room_modes[m].freq;
                    float nearest_int = roundf(ratio);
                    if (fabsf(ratio - nearest_int) < 0.1f) {
                        harmonic_found = true;
                        break;
                    }
                }
                if (!harmonic_found) {
                    results->room_modes[idx].type = 1;  /* tangential */
                }
            }

            ESP_LOGI(TAG, "  Room mode: %.1f Hz, decay=%.3f s, type=%s",
                     freq, results->room_modes[idx].decay_time,
                     results->room_modes[idx].type == 0 ? "axial" :
                     results->room_modes[idx].type == 1 ? "tangential" : "oblique");

            results->num_modes++;
        }
    }

    /* Sort modes by frequency */
    for (int i = 0; i < results->num_modes - 1; i++) {
        for (int j = i + 1; j < results->num_modes; j++) {
            if (results->room_modes[j].freq < results->room_modes[i].freq) {
                float tf = results->room_modes[i].freq;
                float td = results->room_modes[i].decay_time;
                uint8_t tt = results->room_modes[i].type;
                results->room_modes[i].freq = results->room_modes[j].freq;
                results->room_modes[i].decay_time = results->room_modes[j].decay_time;
                results->room_modes[i].type = results->room_modes[j].type;
                results->room_modes[j].freq = tf;
                results->room_modes[j].decay_time = td;
                results->room_modes[j].type = tt;
            }
        }
    }

    ESP_LOGI(TAG, "Found %d room modes", results->num_modes);

    free(fft_buf);
    return 0;
}