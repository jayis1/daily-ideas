/**
 * noise_analyzer.c — Background noise NC curve estimation
 *
 * Captures ambient noise and computes 1/3-octave band SPL levels.
 * Maps to a Noise Criteria (NC) rating by finding the lowest NC
 * contour that the measured spectrum does not exceed at any band.
 *
 * NC contours are defined per ASHRAE standard for 16 1/3-octave
 * bands from 63 Hz to 8 kHz.
 */

#include "noise_analyzer.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "esp_log.h"
#include "esp_dsp.h"

static const char *TAG = "noise";

/* NC contour reference values (dB SPL) for NC-15 through NC-65 */
/* Each row is an NC rating (15, 20, 25, ..., 65) */
/* Columns: 63, 125, 250, 500, 1k, 2k, 4k, 8k Hz */
static const float nc_contours[11][8] = {
    /* NC-15 */ { 34, 24, 17, 12, 9, 7, 6, 5 },
    /* NC-20 */ { 39, 29, 22, 17, 14, 12, 10, 9 },
    /* NC-25 */ { 44, 34, 27, 22, 19, 17, 14, 13 },
    /* NC-30 */ { 49, 39, 32, 27, 24, 22, 19, 18 },
    /* NC-35 */ { 54, 44, 37, 32, 29, 27, 24, 23 },
    /* NC-40 */ { 59, 49, 42, 37, 34, 32, 29, 28 },
    /* NC-45 */ { 64, 54, 47, 42, 39, 37, 34, 33 },
    /* NC-50 */ { 69, 59, 52, 47, 44, 42, 39, 38 },
    /* NC-55 */ { 74, 64, 57, 52, 49, 47, 44, 43 },
    /* NC-60 */ { 79, 69, 62, 57, 54, 52, 49, 48 },
    /* NC-65 */ { 84, 74, 67, 62, 59, 57, 54, 53 },
};

/* 1/3-octave band center frequencies for NC measurement */
static const float nc_band_centers[8] = {
    63, 125, 250, 500, 1000, 2000, 4000, 8000
};

int noise_analyzer_compute_nc(const int16_t *captured, uint32_t num_samples,
                                uint32_t sample_rate,
                                acoustic_results_t *results) {
    ESP_LOGI(TAG, "Computing NC curve from %u samples...", num_samples);

    /* Compute FFT of the ambient noise */
    size_t fft_len = 1;
    while (fft_len < num_samples) fft_len <<= 1;

    float *fft_buf = malloc(fft_len * 2 * sizeof(float));
    if (!fft_buf) return -1;

    /* Convert int16 to float and zero-pad */
    for (uint32_t i = 0; i < num_samples && i < fft_len; i++) {
        fft_buf[i * 2] = (float)captured[i] / 32768.0f;
        fft_buf[i * 2 + 1] = 0.0f;
    }
    for (size_t i = num_samples; i < fft_len; i++) {
        fft_buf[i * 2] = 0.0f;
        fft_buf[i * 2 + 1] = 0.0f;
    }

    dsps_fft2r_fc32(fft_buf, fft_len);
    dsps_bit_rev_fc32(fft_buf, fft_len);

    float bin_hz = (float)sample_rate / fft_len;

    /* Compute RMS level per NC band */
    float band_spl[8] = {0};
    float mic_sensitivity = -26.0f;  /* dBFS at 94 dB SPL (ICS-43434) */
    float ref_spl = 94.0f;

    for (int b = 0; b < 8; b++) {
        float fc = nc_band_centers[b];
        float fl = fc / 1.1225f;
        float fh = fc * 1.1225f;
        int bin_lo = (int)(fl / bin_hz);
        int bin_hi = (int)(fh / bin_hz);
        if (bin_lo < 0) bin_lo = 0;
        if (bin_hi >= (int)fft_len / 2) bin_hi = fft_len / 2 - 1;

        /* RMS energy in this band */
        double energy = 0.0;
        int count = 0;
        for (int k = bin_lo; k <= bin_hi; k++) {
            float re = fft_buf[k * 2] / fft_len;
            float im = fft_buf[k * 2 + 1] / fft_len;
            energy += (double)(re * re + im * im);
            count++;
        }

        float rms = (count > 0) ? sqrtf((float)(energy / count)) : 1e-10f;
        float dbfs = 20.0f * log10f(rms + 1e-10f);

        /* Convert dBFS to dB SPL using mic sensitivity */
        band_spl[b] = dbfs - mic_sensitivity + ref_spl;

        ESP_LOGD(TAG, "  Band %.0f Hz: %.1f dB SPL", fc, band_spl[b]);
    }

    /* Store in results (map 8 NC bands to nc_bands array) */
    for (int b = 0; b < 8 && b < NUM_NC_BANDS; b++) {
        results->nc_bands[b] = band_spl[b];
    }

    /* Determine NC rating: find the lowest NC contour that is
       not exceeded by the measured spectrum at any band */
    float nc_rating = 65.0f;
    for (int nc = 0; nc < 11; nc++) {
        bool fits = true;
        for (int b = 0; b < 8; b++) {
            if (band_spl[b] > nc_contours[nc][b]) {
                fits = false;
                break;
            }
        }
        if (fits) {
            nc_rating = 15.0f + nc * 5.0f;
            break;
        }
    }

    results->nc_rating = nc_rating;
    ESP_LOGI(TAG, "NC rating: NC-%.0f", nc_rating);

    free(fft_buf);
    return 0;
}