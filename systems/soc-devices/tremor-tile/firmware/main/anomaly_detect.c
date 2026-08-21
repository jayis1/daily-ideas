/*
 * Tremor Tile — Anomaly Detection
 * anomaly_detect.c — Baseline learning, deviation detection, alert generation
 *
 * Learns the normal vibration signature during a calibration period,
 * then flags anomalies when the current spectral signature deviates
 * significantly from the baseline.
 */

#include "anomaly_detect.h"
#include "fft_engine.h"
#include "config.h"
#include <math.h>
#include <string.h>
#include <stdio.h>

// Baseline statistics for each feature
typedef struct {
    float mean;
    float std_dev;
    float min;
    float max;
    uint32_t sample_count;
} feature_stats_t;

// Full baseline model
typedef struct {
    // Per-peak stats (position and amplitude)
    feature_stats_t peak_freq_stats[NUM_PEAK_FREQUENCIES];
    feature_stats_t peak_amp_stats[NUM_PEAK_FREQUENCIES];

    // Per-band energy stats
    feature_stats_t band_energy_stats[NUM_FREQ_BANDS];

    // Time-domain stats
    feature_stats_t rms_stats;
    feature_stats_t crest_factor_stats;
    feature_stats_t kurtosis_stats;

    // Model metadata
    bool is_learned;
    uint32_t total_samples;
    int64_t learn_start_time;
    int64_t learn_end_time;
    uint32_t magic;  // Validation marker
} baseline_model_t;

// Magic number for flash validation
#define BASELINE_MAGIC 0x54524D52  // "TRMR"

// Global state
static baseline_model_t baseline;
static bool learning_mode = true;
static float anomaly_threshold = ANOMALY_THRESHOLD_SIGMA;
static alert_t pending_alert;
static bool alert_pending = false;

// Running accumulators for learning
static float peak_freq_accum[NUM_PEAK_FREQUENCIES];
static float peak_freq_sq_accum[NUM_PEAK_FREQUENCIES];
static float band_energy_accum[NUM_FREQ_BANDS];
static float band_energy_sq_accum[NUM_FREQ_BANDS];
static float rms_accum;
static float rms_sq_accum;
static float kurtosis_accum;
static float kurtosis_sq_accum;
static uint32_t learning_samples = 0;

// Initialize anomaly detection
void anomaly_detect_init(void) {
    // Try to load baseline from flash
    // For now, start fresh (in production, load from W25Q128)
    memset(&baseline, 0, sizeof(baseline_model_t));
    baseline.is_learned = false;
    learning_mode = true;
    learning_samples = 0;

    // Reset accumulators
    memset(peak_freq_accum, 0, sizeof(peak_freq_accum));
    memset(peak_freq_sq_accum, 0, sizeof(peak_freq_sq_accum));
    memset(band_energy_accum, 0, sizeof(band_energy_accum));
    memset(band_energy_sq_accum, 0, sizeof(band_energy_sq_accum));
    rms_accum = 0.0f;
    rms_sq_accum = 0.0f;
    kurtosis_accum = 0.0f;
    kurtosis_sq_accum = 0.0f;

    printf("Anomaly: Initialized — learning mode active (24h baseline)\n");
}

// Update statistics with a new sample (during learning phase)
static void update_feature_stats(feature_stats_t *stats, float value, float *accum, float *sq_accum) {
    *accum += value;
    *sq_accum += value * value;

    if (value < stats->min || stats->sample_count == 0) {
        stats->min = value;
    }
    if (value > stats->max) {
        stats->max = value;
    }
    stats->sample_count++;
}

// Evaluate current spectral features against baseline
anomaly_result_t anomaly_detect_evaluate(spectral_features_t *features) {
    anomaly_result_t result;
    memset(&result, 0, sizeof(anomaly_result_t));
    result.is_anomaly = false;
    result.severity = 0;
    result.affected_bands = 0;
    result.type = 0;
    result.timestamp = features->timestamp;

    if (learning_mode) {
        // Accumulate statistics during learning phase
        for (int i = 0; i < features->num_peaks; i++) {
            update_feature_stats(&baseline.peak_freq_stats[i],
                                 features->peak_freqs[i],
                                 &peak_freq_accum[i],
                                 &peak_freq_sq_accum[i]);
            update_feature_stats(&baseline.peak_amp_stats[i],
                                 features->peak_amplitudes[i],
                                 NULL, NULL);
        }

        for (int b = 0; b < NUM_FREQ_BANDS; b++) {
            update_feature_stats(&baseline.band_energy_stats[b],
                                 features->band_energies[b],
                                 &band_energy_accum[b],
                                 &band_energy_sq_accum[b]);
        }

        update_feature_stats(&baseline.rms_stats, features->rms,
                            &rms_accum, &rms_sq_accum);
        update_feature_stats(&baseline.crest_factor_stats, features->crest_factor,
                            NULL, NULL);
        update_feature_stats(&baseline.kurtosis_stats, features->kurtosis,
                            &kurtosis_accum, &kurtosis_sq_accum);

        learning_samples++;

        // Check if learning period is complete
        // At 400Hz with 1024-sample FFTs (50% overlap), we get ~0.78 FFTs/sec
        // 24 hours × 0.78 = ~67,000 FFTs. We'll use a simplified check.
        // For testing, we complete learning after 1000 samples (~20 min)
        if (learning_samples >= 1000) {
            // Finalize baseline statistics
            finalize_baseline();
            learning_mode = false;
            printf("Anomaly: Baseline learning complete (%lu samples)\n", learning_samples);
        }

        return result;  // No anomaly detection during learning
    }

    // === Anomaly Detection Phase ===
    float max_severity = 0.0f;

    // 1. Check for new spectral peaks (peaks that weren't in baseline)
    for (int i = 0; i < features->num_peaks; i++) {
        // Find the nearest baseline peak
        float min_dist = 1e6f;
        for (int j = 0; j < NUM_PEAK_FREQUENCIES; j++) {
            if (baseline.peak_freq_stats[j].sample_count > 0) {
                float dist = fabsf(features->peak_freqs[i] - baseline.peak_freq_stats[j].mean);
                if (dist < min_dist) min_dist = dist;
            }
        }

        // If this peak is far from any baseline peak, it's a new peak
        if (min_dist > 5.0f) {  // More than 5 Hz away from any baseline peak
            float peak_sigma = 0.0f;
            if (baseline.peak_amp_stats[i].std_dev > 0) {
                peak_sigma = fabsf(features->peak_amplitudes[i] - baseline.peak_amp_stats[i].mean)
                            / baseline.peak_amp_stats[i].std_dev;
            }

            if (peak_sigma > NEW_PEAK_THRESHOLD_SIGMA) {
                result.is_anomaly = true;
                result.type = ALERT_NEW_PEAK;
                float severity = fminf(10.0f, peak_sigma / 2.0f);
                max_severity = fmaxf(max_severity, severity);
            }
        }
    }

    // 2. Check for peak frequency shifts
    for (int i = 0; i < features->num_peaks && i < NUM_PEAK_FREQUENCIES; i++) {
        if (baseline.peak_freq_stats[i].sample_count > 0 && baseline.peak_freq_stats[i].mean > 0) {
            float shift = fabsf(features->peak_freqs[i] - baseline.peak_freq_stats[i].mean)
                         / baseline.peak_freq_stats[i].mean;

            if (shift > PEAK_SHIFT_THRESHOLD) {
                result.is_anomaly = true;
                result.type = ALERT_PEAK_SHIFT;
                float severity = fminf(10.0f, shift * 20.0f);
                max_severity = fmaxf(max_severity, severity);
            }
        }
    }

    // 3. Check band energies
    for (int b = 0; b < NUM_FREQ_BANDS; b++) {
        if (baseline.band_energy_stats[b].sample_count > 0 && baseline.band_energy_stats[b].std_dev > 0) {
            float sigma = fabsf(features->band_energies[b] - baseline.band_energy_stats[b].mean)
                         / baseline.band_energy_stats[b].std_dev;

            if (sigma > anomaly_threshold) {
                result.is_anomaly = true;
                result.type = ALERT_BAND_ENERGY;
                result.affected_bands |= (1 << b);
                float severity = fminf(10.0f, sigma / 2.0f);
                max_severity = fmaxf(max_severity, severity);
            }
        }
    }

    // 4. Check RMS
    if (baseline.rms_stats.sample_count > 0 && baseline.rms_stats.std_dev > 0) {
        float rms_sigma = fabsf(features->rms - baseline.rms_stats.mean)
                         / baseline.rms_stats.std_dev;

        if (rms_sigma > RMS_THRESHOLD_SIGMA) {
            result.is_anomaly = true;
            result.type = ALERT_RMS_INCREASE;
            float severity = fminf(10.0f, rms_sigma / 2.0f);
            max_severity = fmaxf(max_severity, severity);
        }
    }

    // 5. Check kurtosis (impulsive events)
    if (baseline.kurtosis_stats.sample_count > 0 && baseline.kurtosis_stats.std_dev > 0) {
        float kurt_sigma = fabsf(features->kurtosis - baseline.kurtosis_stats.mean)
                          / baseline.kurtosis_stats.std_dev;

        if (kurt_sigma > KURTOSIS_THRESHOLD_SIGMA) {
            result.is_anomaly = true;
            result.type = ALERT_KURTOSIS;
            float severity = fminf(10.0f, kurt_sigma / 2.0f);
            max_severity = fmaxf(max_severity, severity);
        }
    }

    result.severity = (uint8_t)fmaxf(1.0f, fminf(10.0f, max_severity));

    return result;
}

// Finalize baseline after learning period
static void finalize_baseline(void) {
    // Compute mean and std_dev for accumulated statistics
    for (int i = 0; i < NUM_PEAK_FREQUENCIES; i++) {
        if (baseline.peak_freq_stats[i].sample_count > 1) {
            baseline.peak_freq_stats[i].mean = peak_freq_accum[i] / baseline.peak_freq_stats[i].sample_count;
            float mean_sq = peak_freq_sq_accum[i] / baseline.peak_freq_stats[i].sample_count;
            baseline.peak_freq_stats[i].std_dev = sqrtf(mean_sq - baseline.peak_freq_stats[i].mean * baseline.peak_freq_stats[i].mean);
        }
    }

    for (int b = 0; b < NUM_FREQ_BANDS; b++) {
        if (baseline.band_energy_stats[b].sample_count > 1) {
            baseline.band_energy_stats[b].mean = band_energy_accum[b] / baseline.band_energy_stats[b].sample_count;
            float mean_sq = band_energy_sq_accum[b] / baseline.band_energy_stats[b].sample_count;
            baseline.band_energy_stats[b].std_dev = sqrtf(mean_sq - baseline.band_energy_stats[b].mean * baseline.band_energy_stats[b].mean);
        }
    }

    if (baseline.rms_stats.sample_count > 1) {
        baseline.rms_stats.mean = rms_accum / baseline.rms_stats.sample_count;
        float mean_sq = rms_sq_accum / baseline.rms_stats.sample_count;
        baseline.rms_stats.std_dev = sqrtf(mean_sq - baseline.rms_stats.mean * baseline.rms_stats.mean);
    }

    if (baseline.kurtosis_stats.sample_count > 1) {
        baseline.kurtosis_stats.mean = kurtosis_accum / baseline.kurtosis_stats.sample_count;
        float mean_sq = kurtosis_sq_accum / baseline.kurtosis_stats.sample_count;
        baseline.kurtosis_stats.std_dev = sqrtf(mean_sq - baseline.kurtosis_stats.mean * baseline.kurtosis_stats.mean);
    }

    baseline.is_learned = true;
    baseline.total_samples = learning_samples;
    baseline.magic = BASELINE_MAGIC;

    // TODO: Save to flash (W25Q128)
    printf("Anomaly: Baseline finalized — RMS mean=%.4fg, std=%.4fg\n",
           baseline.rms_stats.mean, baseline.rms_stats.std_dev);
}

// Flag an alert for Core 0 to transmit
void anomaly_detect_flag_alert(anomaly_result_t *result) {
    pending_alert.type = result->type;
    pending_alert.severity = result->severity;
    pending_alert.affected_bands = result->affected_bands;
    pending_alert.timestamp = result->timestamp;
    alert_pending = true;
}

// Check if an alert is pending (called by Core 0)
bool anomaly_detect_alert_pending(void) {
    return alert_pending;
}

// Get the pending alert (called by Core 0)
alert_t anomaly_detect_get_alert(void) {
    alert_pending = false;
    return pending_alert;
}

// Reset baseline (start learning again)
void anomaly_detect_reset_baseline(void) {
    learning_mode = true;
    learning_samples = 0;
    memset(&baseline, 0, sizeof(baseline_model_t));
    memset(peak_freq_accum, 0, sizeof(peak_freq_accum));
    memset(peak_freq_sq_accum, 0, sizeof(peak_freq_sq_accum));
    memset(band_energy_accum, 0, sizeof(band_energy_accum));
    memset(band_energy_sq_accum, 0, sizeof(band_energy_sq_accum));
    rms_accum = 0.0f;
    rms_sq_accum = 0.0f;
    kurtosis_accum = 0.0f;
    kurtosis_sq_accum = 0.0f;
    printf("Anomaly: Baseline reset — restarting learning\n");
}

// Set anomaly threshold (sigma multiplier)
void anomaly_detect_set_threshold(float sigma) {
    anomaly_threshold = sigma;
    printf("Anomaly: Threshold set to %.1fσ\n", sigma);
}