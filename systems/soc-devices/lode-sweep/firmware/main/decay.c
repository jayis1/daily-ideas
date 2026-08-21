/*
 * lode-sweep / firmware / decay.c
 * Decay curve processing: 16-gate extraction, normalization, feature vector.
 *
 * The raw ADC buffer contains 16 gates × 16 oversample samples.
 * Each gate is averaged (oversample) to produce one value, yielding a
 * 16-element decay curve. The curve is then normalized to 0..1 (dividing
 * by the max gate value) for shape-based classification.
 */
#include "main.h"

void decay_init(void)
{
    /* No state to initialize */
}

/*
 * Extract 16 gate values from the raw ADC buffer.
 * Each gate = average of GATE_OVERSAMPLE (16) consecutive samples,
 * with the DC offset (ADC mid-scale) removed.
 */
void decay_extract(const int16_t *raw, float *gates)
{
    const int32_t dc_offset = 2048;  /* 12-bit ADC mid-scale (AC-coupled) */

    for (int g = 0; g < NUM_GATES; g++) {
        int32_t sum = 0;
        for (int s = 0; s < GATE_OVERSAMPLE; s++) {
            int32_t sample = (int32_t)raw[g * GATE_OVERSAMPLE + s] - dc_offset;
            sum += sample;
        }
        /* Average and convert to voltage (3.3 V / 4096 = 0.806 mV/LSB) */
        float avg = (float)sum / (float)GATE_OVERSAMPLE;
        gates[g] = avg * 0.000806f;  /* volts */
    }
}

/*
 * Normalize the decay curve to 0..1 by dividing by the max gate value.
 * This makes the curve shape independent of target size and depth,
 * so the k-NN classifier works on shape alone.
 */
void decay_normalize(float *gates)
{
    float maxv = 1e-9f;
    for (int i = 0; i < NUM_GATES; i++) {
        if (gates[i] > maxv) maxv = gates[i];
    }
    float inv = 1.0f / maxv;
    for (int i = 0; i < NUM_GATES; i++) {
        gates[i] *= inv;
    }
}

/*
 * Compute the effective decay time constant (τ) from the 16-gate curve.
 * Fits gates to A * exp(-t/τ) via log-linear regression.
 * Returns τ in microseconds, or 0 if fit fails.
 */
float decay_estimate_tau(const float *gates)
{
    /* log(gate[i]) = log(A) - t[i]/τ
       Linear regression: y = a + b*t, where y=ln(gate), b = -1/τ */
    double sum_t = 0, sum_y = 0, sum_ty = 0, sum_t2 = 0;
    int n = 0;

    for (int i = 0; i < NUM_GATES; i++) {
        if (gates[i] <= 1e-6f) continue;
        float t = GATE_DELAY_US[i];
        float y = logf(gates[i]);
        sum_t  += t;
        sum_y  += y;
        sum_ty += t * y;
        sum_t2 += t * t;
        n++;
    }

    if (n < 3) return 0.0f;

    double denom = (double)n * sum_t2 - sum_t * sum_t;
    if (fabs(denom) < 1e-12) return 0.0f;

    double b = ((double)n * sum_ty - sum_t * sum_y) / denom;
    if (b >= 0) return 0.0f;   /* should be negative for decay */

    return (float)(-1.0 / b);  /* τ in µs */
}