/*
 * Hive Mind — Acoustic Analyzer
 * I2S MEMS microphone capture + FFT + bee colony state classification
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "acoustic_analyzer.h"
#include "main.h"
#include <math.h>
#include <string.h>

#define FFT_SIZE       256
#define SAMPLE_RATE    8000   /* 8 kHz sampling */
#define DMA_BUF_SIZE   (FFT_SIZE * 2)  /* Stereo I2S, we use one channel */

/* FFT input/output buffers (float for arm_math or custom) */
static float fft_input[FFT_SIZE];
static float fft_magnitude[FFT_SIZE / 2];

/* I2S DMA buffer: 16-bit samples, stereo */
static int16_t i2s_dma_buf[DMA_BUF_SIZE];

/* Frequency bin width: SAMPLE_RATE / FFT_SIZE = 31.25 Hz */
#define BIN_WIDTH  (SAMPLE_RATE / (float)FFT_SIZE)

/* Acoustic classification frequency bands (in bins) */
#define BIN_200   (int)(200.0f / BIN_WIDTH)   /* bin 6 */
#define BIN_250   (int)(250.0f / BIN_WIDTH)   /* bin 8 */
#define BIN_300   (int)(300.0f / BIN_WIDTH)   /* bin 9 */
#define BIN_400   (int)(400.0f / BIN_WIDTH)   /* bin 12 */
#define BIN_500   (int)(500.0f / BIN_WIDTH)   /* bin 16 */
#define BIN_600   (int)(600.0f / BIN_WIDTH)   /* bin 19 */
#define BIN_800   (int)(800.0f / BIN_WIDTH)   /* bin 25 */
#define BIN_1000  (int)(1000.0f / BIN_WIDTH)  /* bin 32 */

extern I2S_HandleTypeDef hi2s2;

/* ------------------------------------------------------------------ */
/* FFT implementation (Cooley-Tukey radix-2, in-place)                 */
/* ------------------------------------------------------------------ */

static void fft_radix2(float *real, float *imag, int n)
{
    /* Bit-reversal permutation */
    int j = 0;
    for (int i = 0; i < n - 1; i++) {
        if (i < j) {
            float tmp_r = real[i]; real[i] = real[j]; real[j] = tmp_r;
            float tmp_i = imag[i]; imag[i] = imag[j]; imag[j] = tmp_i;
        }
        int k = n >> 1;
        while (k <= j) { j -= k; k >>= 1; }
        j += k;
    }

    /* Butterfly operations */
    for (int len = 2; len <= n; len <<= 1) {
        float angle = -2.0f * M_PI / len;
        float w_r = cosf(angle);
        float w_i = sinf(angle);

        for (int i = 0; i < n; i += len) {
            float cur_r = 1.0f, cur_i = 0.0f;
            for (int k = 0; k < len / 2; k++) {
                float t_r = cur_r * real[i + k + len/2] - cur_i * imag[i + k + len/2];
                float t_i = cur_r * imag[i + k + len/2] + cur_i * real[i + k + len/2];
                real[i + k + len/2] = real[i + k] - t_r;
                imag[i + k + len/2] = imag[i + k] - t_i;
                real[i + k] += t_r;
                imag[i + k] += t_i;
                float new_r = cur_r * w_r - cur_i * w_i;
                cur_i = cur_r * w_i + cur_i * w_r;
                cur_r = new_r;
            }
        }
    }
}

/* ------------------------------------------------------------------ */
/* I2S capture                                                          */
/* ------------------------------------------------------------------ */

static volatile uint8_t i2s_capture_done = 0;

void HAL_I2S_RxCpltCallback(I2S_HandleTypeDef *hi2s)
{
    if (hi2s->Instance == SPI2) {
        i2s_capture_done = 1;
    }
}

static int capture_audio(void)
{
    i2s_capture_done = 0;
    HAL_StatusTypeDef ret = HAL_I2S_Receive_DMA(&hi2s2, (uint16_t *)i2s_dma_buf, DMA_BUF_SIZE);
    if (ret != HAL_OK) return -1;

    /* Wait for DMA completion (2 seconds of audio at 8 kHz × 2 channels) */
    uint32_t timeout = HAL_GetTick() + 3000;
    while (!i2s_capture_done) {
        if (HAL_GetTick() > timeout) return -1;
        /* Yield to other tasks */
    }

    /* Stop DMA */
    HAL_I2S_DMAStop(&hi2s2);

    /* Extract left channel (ICS-43434 uses left channel) */
    for (int i = 0; i < FFT_SIZE && i < DMA_BUF_SIZE / 2; i++) {
        fft_input[i] = (float)i2s_dma_buf[i * 2];  /* Left channel, 16-bit */
    }

    return 0;
}

/* ------------------------------------------------------------------ */
/* Classification                                                      */
/* ------------------------------------------------------------------ */

static float band_energy(int lo_bin, int hi_bin)
{
    float sum = 0.0f;
    for (int i = lo_bin; i <= hi_bin && i < FFT_SIZE / 2; i++) {
        sum += fft_magnitude[i];
    }
    return sum;
}

static acoustic_class_t classify(float *dominant_freq)
{
    float e_200_250 = band_energy(BIN_200, BIN_250);  /* Normal hum */
    float e_250_300 = band_energy(BIN_250, BIN_300);   /* Elevated activity */
    float e_300_400 = band_energy(BIN_300, BIN_400);   /* Piping */
    float e_400_500 = band_energy(BIN_400, BIN_500);   /* Fanning */
    float e_500_800 = band_energy(BIN_500, BIN_800);   /* High activity */
    float e_800_up  = band_energy(BIN_800, BIN_1000);  /* Wideband */
    float e_total   = e_200_250 + e_250_300 + e_300_400 + e_400_500 + e_500_800 + e_800_up;

    /* Find dominant frequency */
    float max_mag = 0;
    int max_bin = 0;
    for (int i = 1; i < FFT_SIZE / 2; i++) {
        if (fft_magnitude[i] > max_mag) {
            max_mag = fft_magnitude[i];
            max_bin = i;
        }
    }
    *dominant_freq = max_bin * BIN_WIDTH;

    /* Avoid division by zero */
    if (e_total < 100.0f) {
        return AC_DEAD;  /* Silence = dead colony or extreme cold */
    }

    /* Rule-based classification */
    float r_piping = e_300_400 / e_total;
    float r_fanning = e_400_500 / e_total;
    float r_hum = e_200_250 / e_total;
    float r_high = (e_500_800 + e_800_up) / e_total;

    /* Piping: strong 300-400 Hz */
    if (r_piping > 0.4f) {
        return AC_PIPING;
    }

    /* Fanning: strong 400-500 Hz */
    if (r_fanning > 0.35f) {
        return AC_FANNING;
    }

    /* Swarming: very high overall energy, wideband */
    if (r_high > 0.4f && e_total > 50000.0f) {
        return AC_SWARMING;
    }

    /* Robbing: elevated high-freq + moderate hum */
    if (r_high > 0.3f && r_hum < 0.3f) {
        return AC_ROBBING;
    }

    /* Queenless: weak hum, no clear peak */
    if (r_hum < 0.15f && e_total < 10000.0f) {
        return AC_QUEENLESS;
    }

    /* Clustering: moderate hum with weak fundamentals (cold cluster) */
    if (r_hum > 0.2f && e_total < 20000.0f && *dominant_freq < 220.0f) {
        return AC_CLUSTERING;
    }

    /* Normal: healthy hum at 200-250 Hz */
    if (r_hum > 0.25f) {
        return AC_QUEENRIGHT;
    }

    /* Default fallback */
    return AC_QUEENRIGHT;
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

void acoustic_analyzer_init(void)
{
    /* I2S is initialized by MX_I2S2_Init() in main.c */
    memset(fft_input, 0, sizeof(fft_input));
    memset(fft_magnitude, 0, sizeof(fft_magnitude));
}

acoustic_result_t acoustic_analyzer_classify(void)
{
    acoustic_result_t result = {AC_QUEENRIGHT, 0};

    /* Capture 2 seconds of audio via I2S DMA */
    if (capture_audio() != 0) {
        result.cls = AC_DEAD;  /* Sensor failure */
        result.dominant_freq_hz = 0;
        return result;
    }

    /* Apply Hann window */
    for (int i = 0; i < FFT_SIZE; i++) {
        float w = 0.5f * (1.0f - cosf(2.0f * M_PI * i / (FFT_SIZE - 1)));
        fft_input[i] *= w;
    }

    /* Run FFT */
    float imag[FFT_SIZE];
    memset(imag, 0, sizeof(imag));
    fft_radix2(fft_input, imag, FFT_SIZE);

    /* Compute magnitude spectrum */
    for (int i = 0; i < FFT_SIZE / 2; i++) {
        fft_magnitude[i] = sqrtf(fft_input[i] * fft_input[i] + imag[i] * imag[i]);
    }

    /* Classify */
    result.cls = classify(&result.dominant_freq_hz);

    return result;
}

const char *acoustic_class_name(acoustic_class_t cls)
{
    static const char *names[] = {
        "QUEENRIGHT", "QUEENLESS", "SWARMING", "FANNING",
        "PIPING", "ROBBING", "CLUSTERING", "DEAD"
    };
    if (cls < 0 || cls >= AC_MAX) return "UNKNOWN";
    return names[cls];
}