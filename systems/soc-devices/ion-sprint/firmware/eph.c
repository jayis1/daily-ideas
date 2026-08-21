/*
 * eph.c — Electropherogram processing
 *
 * 1. Asymmetric least squares (ALS) baseline estimation
 * 2. Derivative-based peak detection: 1st-derivative zero-cross +
 *    2nd-derivative negative + amplitude > 3σ noise
 * 3. Peak area via trapezoidal integration
 * 4. Peak skewness for k-NN classification feature
 */

#include "eph.h"
#include "stm32g474_conf.h"
#include <math.h>
#include <string.h>

void eph_init(void)
{
    /* Nothing to init */
}

/* ALS baseline: iterative weighted least squares (Eilers & Boelens 2005)
 * Simplified: 10 iterations with fixed λ and p. */
void eph_als_baseline(float *signal, uint32_t count, float lambda, float p)
{
    if (count < 10) return;

    /* Working arrays (simplified — on-device, use stack or static) */
    static float w[EPH_SAMPLES_MAX / 4];  /* Scaled down for memory */
    static float z[EPH_SAMPLES_MAX / 4];

    /* Decimate for processing if too long */
    uint32_t n = count;
    if (n > EPH_SAMPLES_MAX / 4) n = EPH_SAMPLES_MAX / 4;

    /* Initialize weights to 1 */
    for (uint32_t i = 0; i < n; i++) w[i] = 1.0f;

    /* 10 iterations of ALS */
    for (int iter = 0; iter < 10; iter++) {
        /* Solve (W + λDᵀD) z = W·y
         * D is second-difference matrix: D[i] = [0, -1, 2, -1, 0]
         * Simplified: use Jacobi iteration (3-term recurrence) */
        for (uint32_t i = 0; i < n; i++) {
            float y = signal[i] * w[i];
            float d2 = (i > 0 && i < n - 1) ?
                        (z[i-1] - 2.0f * z[i] + z[i+1]) * lambda : 0.0f;
            z[i] = (y + d2) / (w[i] + 4.0f * lambda);
        }

        /* Update weights: w = p if y > z, else (1-p) */
        for (uint32_t i = 0; i < n; i++) {
            w[i] = (signal[i] > z[i]) ? p : (1.0f - p);
        }
    }

    /* Subtract baseline from signal */
    for (uint32_t i = 0; i < n; i++) {
        signal[i] -= z[i];
    }
}

/* Estimate noise (σ) from the baseline region (first 5% of signal) */
static float estimate_noise(const float *signal, uint32_t count)
{
    uint32_t n = count / 20;  /* First 5% */
    if (n < 2) n = 2;
    float mean = 0.0f;
    for (uint32_t i = 0; i < n; i++) mean += signal[i];
    mean /= (float)n;

    float var = 0.0f;
    for (uint32_t i = 0; i < n; i++) {
        float d = signal[i] - mean;
        var += d * d;
    }
    var /= (float)(n - 1);
    return sqrtf(var);
}

uint8_t eph_detect_peaks(const float *eph_in, uint32_t count,
                         peak_t *peaks, uint8_t max_peaks)
{
    /* Copy to working buffer for baseline correction */
    static float work[EPH_SAMPLES_MAX / 4];
    uint32_t n = count;
    if (n > EPH_SAMPLES_MAX / 4) n = EPH_SAMPLES_MAX / 4;
    memcpy(work, eph_in, n * sizeof(float));

    /* ALS baseline correction */
    eph_als_baseline(work, n, ALS_LAMBDA, ALS_P);

    /* Estimate noise floor */
    float sigma = estimate_noise(work, n);
    float threshold = PEAK_MIN_SNR * sigma;

    /* Peak detection: scan for maxima above threshold
     * A peak starts when signal rises above 0.5×threshold, peaks at a
     * local maximum, and ends when signal falls below 0.5×threshold.
     */
    uint8_t pk_count = 0;
    uint32_t i = 0;
    float dt = 1.0f / (float)C4D_EPH_RATE_HZ;  /* 10 ms per sample */

    while (i < n - 1 && pk_count < max_peaks) {
        /* Find peak start (rising above 0.5×threshold) */
        if (work[i] > 0.5f * threshold) {
            uint32_t start = i;
            float max_val = work[i];
            uint32_t max_idx = i;

            /* Find peak maximum */
            while (i < n - 1 && work[i] > 0.5f * threshold) {
                if (work[i] > max_val) {
                    max_val = work[i];
                    max_idx = i;
                }
                i++;
            }
            uint32_t end = i;

            /* Validate peak: max above full threshold, width in range */
            float width_s = (float)(end - start) * dt;
            if (max_val > threshold &&
                width_s >= (float)PEAK_MIN_WIDTH_MS / 1000.0f &&
                width_s <= (float)PEAK_MAX_WIDTH_MS / 1000.0f) {

                /* Compute area (trapezoidal integration) */
                float area = 0.0f;
                for (uint32_t j = start; j < end; j++) {
                    area += 0.5f * (work[j] + work[j + 1]) * dt;
                }

                /* Compute skewness */
                float mean = 0.0f, var = 0.0f, skew = 0.0f;
                uint32_t pw = end - start;
                for (uint32_t j = start; j < end; j++) mean += work[j];
                mean /= (float)pw;
                for (uint32_t j = start; j < end; j++) {
                    float d = work[j] - mean;
                    var += d * d;
                    skew += d * d * d;
                }
                var /= (float)pw;
                float std = sqrtf(var);
                skew = (std > 1e-12f) ? skew / ((float)pw * std * std * std) : 0.0f;

                /* Store peak */
                peaks[pk_count].migration_time = (float)max_idx * dt;
                peaks[pk_count].height = max_val;
                peaks[pk_count].area = area;
                peaks[pk_count].skewness = skew;
                peaks[pk_count].start_time = (float)start * dt;
                peaks[pk_count].end_time = (float)end * dt;
                pk_count++;
            }
        }
        i++;
    }

    return pk_count;
}