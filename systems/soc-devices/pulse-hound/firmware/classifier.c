/*
 * Pulse Hound — RF Signal Hunter
 * classifier.c — Temporal envelope analysis and signal classification
 *
 * Analyzes the RSSI time-series to classify the likely signal type:
 * continuous, bursty (WiFi/BLE), pulsed (cellular), radar, or unknown.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "classifier.h"
#include "spectrum.h"
#include "config.h"
#include <math.h>
#include <string.h>

/* ---- HAL stubs ---- */
extern void delay_ms(uint32_t ms);

/* ---- Classification state ---- */
static signal_class_t current_class = CLASS_UNKNOWN;
static float current_confidence = 0.0f;

/* ---- Helper: compute mean ---- */
static float compute_mean(const float *data, int n)
{
    float sum = 0.0f;
    for (int i = 0; i < n; i++) sum += data[i];
    return sum / (float)n;
}

/* ---- Helper: compute variance ---- */
static float compute_variance(const float *data, int n, float mean)
{
    float sum = 0.0f;
    for (int i = 0; i < n; i++) {
        float d = data[i] - mean;
        sum += d * d;
    }
    return sum / (float)n;
}

/* ---- Helper: autocorrelation at a given lag ---- */
static float autocorrelation(const float *data, int n, int lag)
{
    if (lag >= n) return 0.0f;
    float sum = 0.0f;
    float mean = compute_mean(data, n);
    for (int i = 0; i < n - lag; i++) {
        sum += (data[i] - mean) * (data[i + lag] - mean);
    }
    return sum / (float)(n - lag);
}

/* ---- Helper: find dominant period in the autocorrelation ---- */
static float find_dominant_period_ms(const float *data, int n, int sample_hz)
{
    int max_lag = n / 2;
    float max_acf = 0.0f;
    int best_lag = 0;

    for (int lag = 1; lag < max_lag; lag++) {
        float acf = autocorrelation(data, n, lag);
        if (acf > max_acf) {
            max_acf = acf;
            best_lag = lag;
        }
    }

    if (best_lag == 0) return 0.0f;
    return (float)best_lag * (1000.0f / (float)sample_hz);
}

/* ---- Classification engine ---- */
signal_class_t classifier_run(void)
{
    float samples[CLASS_SAMPLE_HZ * CLASS_WINDOW_S]; /* 500 samples @ 100 Hz */
    int n = spectrum_get_history(samples, CLASS_SAMPLE_HZ * CLASS_WINDOW_S);
    if (n < 32) {
        current_class = CLASS_UNKNOWN;
        current_confidence = 0.0f;
        return current_class;
    }

    float mean = compute_mean(samples, n);
    float variance = compute_variance(samples, n, mean);
    float std_dev = sqrtf(variance);

    /* --- Threshold-based features --- */

    /* 1. Continuous wave: low variance, stable RSSI */
    if (std_dev < 1.5f && mean > RSSI_NOISE_FLOOR_DBM + 3.0f) {
        current_class = CLASS_CW;
        current_confidence = 0.85f;
        return current_class;
    }

    /* 2. Thermal drift: very slow changes, low variance, near noise floor */
    if (std_dev < 0.5f && mean < RSSI_NOISE_FLOOR_DBM + 2.0f) {
        current_class = CLASS_THERMAL;
        current_confidence = 0.60f;
        return current_class;
    }

    /* 3. Bursty (WiFi/BLE): moderate variance, on/off pattern with 10–100 ms bursts
     *    and 1–4 s gaps. Detect via high kurtosis and periodic on/off pattern. */
    /* Compute on/off ratio: fraction of samples above (mean + 0.5*std) */
    int above_thresh = 0;
    float burst_thresh = mean + 0.5f * std_dev;
    for (int i = 0; i < n; i++) {
        if (samples[i] > burst_thresh) above_thresh++;
    }
    float duty_cycle = (float)above_thresh / (float)n;

    /* 4. Autocorrelation: find dominant period */
    float period_ms = find_dominant_period_ms(samples, n, CLASS_SAMPLE_HZ);

    /* 5. Kurtosis: bursty signals have high kurtosis (heavy tails) */
    float kurt = 0.0f;
    if (variance > 0.01f) {
        for (int i = 0; i < n; i++) {
            float d = samples[i] - mean;
            kurt += d * d * d * d;
        }
        kurt = (kurt / (float)n) / (variance * variance) - 3.0f; /* excess kurtosis */
    }

    /* --- Classification logic --- */

    /* WiFi/BLE: duty cycle 5–30%, period 1–4 s, high kurtosis */
    if (duty_cycle > 0.03f && duty_cycle < 0.35f &&
        period_ms > 500.0f && period_ms < 5000.0f &&
        kurt > 1.0f) {
        current_class = CLASS_WIFI_BLE;
        current_confidence = 0.70f;
        return current_class;
    }

    /* Cellular: very short pulses (0.5–5 ms), period 20–2000 ms
     * At 100 Hz sampling (10 ms), we can't resolve 0.5–5 ms pulses directly,
     * but we see the envelope: bursty with high variance and short period */
    if (duty_cycle > 0.01f && duty_cycle < 0.10f &&
        period_ms > 20.0f && period_ms < 2000.0f &&
        std_dev > 5.0f) {
        current_class = CLASS_CELLULAR;
        current_confidence = 0.55f;
        return current_class;
    }

    /* Radar/UWB: extremely short pulses, would appear as occasional spikes.
     * At 100 Hz we mostly miss these, but they show as very high kurtosis
     * with low duty cycle. */
    if (duty_cycle < 0.05f && kurt > 5.0f && std_dev > 3.0f) {
        current_class = CLASS_RADAR;
        current_confidence = 0.40f;
        return current_class;
    }

    /* Continuous but noisy: maybe analog bug with modulation */
    if (std_dev > 1.5f && std_dev < 5.0f && duty_cycle > 0.5f) {
        current_class = CLASS_CW;
        current_confidence = 0.50f;
        return current_class;
    }

    /* Unknown: signal present but pattern not recognized */
    current_class = CLASS_UNKNOWN;
    current_confidence = 0.30f;
    return current_class;
}

signal_class_t classifier_get_current(void)
{
    return current_class;
}

float classifier_get_confidence(void)
{
    return current_confidence;
}

const char *classifier_label(signal_class_t cls)
{
    switch (cls) {
        case CLASS_CW:       return "CW/Analog";
        case CLASS_WIFI_BLE: return "WiFi/BLE";
        case CLASS_CELLULAR: return "Cellular";
        case CLASS_RADAR:    return "Radar/UWB";
        case CLASS_THERMAL:  return "Thermal";
        case CLASS_UNKNOWN:  return "Unknown";
        default:             return "---";
    }
}