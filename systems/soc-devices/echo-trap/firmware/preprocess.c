/*
 * preprocess.c — Acoustic pre-processing pipeline
 *
 * 1. High-pass filter at 30 Hz (remove wind/traffic rumble)
 * 2. Low-pass filter at 2 kHz (insect wingbeats are <1.5 kHz)
 * 3. RMS energy detector with adaptive noise floor
 * 4. Autocorrelation peak → wingbeat frequency estimate
 *
 * Uses simple biquad filters (direct form I) for efficiency on the ESP32-S3.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "preprocess.h"
#include "esp_log.h"
#include <math.h>
#include <string.h>

static const char *TAG = "preprocess";

/* ---- Biquad filter (direct form I) ---- */
typedef struct {
    float b0, b1, b2;
    float a1, a2;
    float z1, z2;
} biquad_t;

static inline void biquad_init(biquad_t *f, float b0, float b1, float b2,
                                float a1, float a2)
{
    f->b0 = b0; f->b1 = b1; f->b2 = b2;
    f->a1 = a1; f->a2 = a2;
    f->z1 = f->z2 = 0.0f;
}

static inline float biquad_process(biquad_t *f, float x)
{
    float y = f->b0 * x + f->z1;
    f->z1 = f->b1 * x - f->a1 * y + f->z2;
    f->z2 = f->b2 * x - f->a2 * y;
    return y;
}

/* ---- Filter coefficients ---- */
static biquad_t s_hp_filter;   /* high-pass 30 Hz */
static biquad_t s_lp_filter;   /* low-pass 2 kHz */
static float s_noise_floor_dbfs = -60.0f;   /* adaptive noise floor */
static int s_noise_update_counter = 0;

/* Compute biquad coefficients for a high-pass filter */
static void compute_hp_coeffs(biquad_t *f, float cutoff_hz, float sample_rate, float Q)
{
    float w0 = 2.0f * M_PI * cutoff_hz / sample_rate;
    float cos_w0 = cosf(w0);
    float sin_w0 = sinf(w0);
    float alpha = sin_w0 / (2.0f * Q);
    float a0 = 1.0f + alpha;
    f->b0 = ((1.0f + cos_w0) / 2.0f) / a0;
    f->b1 = (1.0f + cos_w0) / a0;
    f->b2 = ((1.0f + cos_w0) / 2.0f) / a0;
    f->a1 = (-2.0f * cos_w0) / a0;
    f->a2 = (1.0f - alpha) / a0;
}

/* Compute biquad coefficients for a low-pass filter */
static void compute_lp_coeffs(biquad_t *f, float cutoff_hz, float sample_rate, float Q)
{
    float w0 = 2.0f * M_PI * cutoff_hz / sample_rate;
    float cos_w0 = cosf(w0);
    float sin_w0 = sinf(w0);
    float alpha = sin_w0 / (2.0f * Q);
    float a0 = 1.0f + alpha;
    f->b0 = ((1.0f - cos_w0) / 2.0f) / a0;
    f->b1 = (1.0f - cos_w0) / a0;
    f->b2 = ((1.0f - cos_w0) / 2.0f) / a0;
    f->a1 = (-2.0f * cos_w0) / a0;
    f->a2 = (1.0f - alpha) / a0;
}

void preprocess_init(void)
{
    ESP_LOGI(TAG, "Initializing pre-processing (HP %.0f Hz, LP %.0f Hz)",
             HP_FILTER_CUTOFF_HZ, LP_FILTER_CUTOFF_HZ);
    compute_hp_coeffs(&s_hp_filter, HP_FILTER_CUTOFF_HZ, I2S_SAMPLE_RATE_HZ, 0.707f);
    compute_lp_coeffs(&s_lp_filter, LP_FILTER_CUTOFF_HZ, I2S_SAMPLE_RATE_HZ, 0.707f);
    s_noise_floor_dbfs = -60.0f;
    s_noise_update_counter = 0;
}

/* RMS in dBFS */
static float compute_rms_dbfs(const float *data, int len)
{
    float sum_sq = 0.0f;
    for (int i = 0; i < len; i++) {
        sum_sq += data[i] * data[i];
    }
    float rms = sqrtf(sum_sq / len);
    if (rms < 1e-7f) return -120.0f;  /* avoid log(0) */
    return 20.0f * log10f(rms / 32768.0f);
}

/* Autocorrelation-based wingbeat frequency estimation.
 * Returns dominant frequency in Hz (0 if none found). */
static float estimate_wingbeat_freq(const float *data, int len, float sample_rate)
{
    /* Compute autocorrelation for lags corresponding to 20 Hz – 1500 Hz */
    int min_lag = (int)(sample_rate / AUTOCORR_MAX_HZ);  /* ~10 samples for 1500 Hz */
    int max_lag = (int)(sample_rate / AUTOCORR_MIN_HZ);  /* ~800 samples for 20 Hz */
    if (max_lag > len / 2) max_lag = len / 2;
    if (min_lag < 1) min_lag = 1;

    float best_corr = 0.0f;
    int best_lag = 0;

    /* Downsample by 4x for efficiency (wingbeats <1.5 kHz → Nyquist >3 kHz OK at 4 kHz) */
    int decim = 4;
    int dec_len = len / decim;
    float sr_dec = sample_rate / decim;
    int dmin = (int)(sr_dec / AUTOCORR_MAX_HZ);
    int dmax = (int)(sr_dec / AUTOCORR_MIN_HZ);
    if (dmax > dec_len / 2) dmax = dec_len / 2;
    if (dmin < 1) dmin = 1;

    for (int lag = dmin; lag <= dmax; lag++) {
        float corr = 0.0f;
        for (int i = 0; i < dec_len - lag; i++) {
            corr += data[i * decim] * data[(i + lag) * decim];
        }
        corr /= (dec_len - lag);
        if (corr > best_corr) {
            best_corr = corr;
            best_lag = lag;
        }
    }

    if (best_lag == 0) return 0.0f;
    return sr_dec / best_lag;
}

int preprocess_frame(const audio_frame_t *frame, preprocess_result_t *result)
{
    /* Filter mic 1 (primary classification channel) */
    static float s_filtered[WINDOW_SAMPLES];
    float max_val = 0.0f;

    for (int i = 0; i < WINDOW_SAMPLES; i++) {
        float s = (float)frame->mic1[i];
        float hp = biquad_process(&s_hp_filter, s);
        float lp = biquad_process(&s_lp_filter, hp);
        s_filtered[i] = lp;
        if (fabsf(lp) > max_val) max_val = fabsf(lp);
    }

    /* Compute RMS energy */
    float rms_dbfs = compute_rms_dbfs(s_filtered, WINDOW_SAMPLES);

    /* Adaptive noise floor update (when no signal is present) */
    s_noise_update_counter++;
    if (rms_dbfs < s_noise_floor_dbfs + 3.0f && s_noise_update_counter > 10) {
        /* Exponential moving average of the noise floor */
        s_noise_floor_dbfs = 0.95f * s_noise_floor_dbfs + 0.05f * rms_dbfs;
        s_noise_update_counter = 0;
    }

    /* Energy gate: is there a signal above the noise floor + threshold? */
    result->has_signal = (rms_dbfs > (s_noise_floor_dbfs + 15.0f) &&
                          rms_dbfs > ENERGY_THRESHOLD_DBFS);
    result->rms_dbfs = rms_dbfs;
    result->noise_floor_dbfs = s_noise_floor_dbfs;

    if (!result->has_signal) {
        result->wingbeat_hz = 0.0f;
        return 0;  /* skip classification — saves CPU */
    }

    /* Estimate wingbeat frequency via autocorrelation */
    float wb_hz = estimate_wingbeat_freq(s_filtered, WINDOW_SAMPLES,
                                          (float)I2S_SAMPLE_RATE_HZ);
    result->wingbeat_hz = wb_hz;

    ESP_LOGD(TAG, "RMS=%.1f dBFS, NF=%.1f, WB=%.1f Hz, signal=%d",
             rms_dbfs, s_noise_floor_dbfs, wb_hz, result->has_signal);

    return 1;  /* interesting frame — proceed to classification */
}