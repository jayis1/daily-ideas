/*
 * lode-sweep / firmware / ground.c
 * Adaptive ground mineralization tracking and cancellation.
 *
 * Soil minerals (magnetite, maghemite) produce a fast-decaying signal
 * (τ_ground ≈ 1–5 µs) that can overwhelm target signals. This module:
 *   1. Models ground as G(t) = A_g * exp(-t/τ_g)
 *   2. Estimates A_g and τ_g from the first few gates (ground-dominated)
 *   3. Subtracts the ground model from all 16 gates each pulse
 *   4. Auto-tracks A_g with an LMS adaptive filter for changing soil
 */
#include "main.h"
#include <math.h>

void ground_init(void)
{
    g_ctx.ground_amp = 0.0f;
    g_ctx.ground_tau = 3.0f;   /* typical ground τ ≈ 3 µs */
}

/*
 * Calibrate the ground model from a ground-only decay curve.
 * Called when no target is present (weak signal or user-initiated).
 *
 * Fits the first 4 gates to A_g * exp(-t/τ_g) via log-linear regression,
 * then stores the parameters in g_ctx.
 */
void ground_calibrate(const float *gates)
{
    /* Use the first 4 gates (10, 12.5, 15.6, 19.5 µs) where ground dominates */
    double sum_t = 0, sum_y = 0, sum_ty = 0, sum_t2 = 0;
    int n = 0;

    for (int i = 0; i < 4; i++) {
        if (gates[i] <= 1e-6f) continue;
        float t = GATE_DELAY_US[i];
        float y = logf(fabsf(gates[i]));
        sum_t  += t;
        sum_y  += y;
        sum_ty += t * y;
        sum_t2 += t * t;
        n++;
    }

    if (n < 3) return;

    double denom = (double)n * sum_t2 - sum_t * sum_t;
    if (fabs(denom) < 1e-12) return;

    double b = ((double)n * sum_ty - sum_t * sum_y) / denom;  /* -1/τ */
    double a = (sum_y - b * sum_t) / n;                        /* ln(A_g) */

    if (b >= 0) return;

    float new_tau = (float)(-1.0 / b);
    float new_amp = (float)exp(a);

    /* Smoothly update ground parameters (low-pass for stability) */
    g_ctx.ground_tau = g_ctx.ground_tau * 0.7f + new_tau * 0.3f;
    g_ctx.ground_amp = g_ctx.ground_amp * 0.5f + new_amp * 0.5f;
}

/*
 * Subtract the adaptive ground model from the 16-gate decay curve.
 * Also performs LMS auto-tracking: updates ground_amp based on the
 * residual in the first few gates.
 */
void ground_balance(float *gates)
{
    const float mu = 0.01f;   /* LMS step size */

    /* Generate ground model at each gate delay */
    float ground_model[NUM_GATES];
    for (int i = 0; i < NUM_GATES; i++) {
        float t = GATE_DELAY_US[i];
        ground_model[i] = g_ctx.ground_amp * expf(-t / g_ctx.ground_tau);
    }

    /* LMS update: use the first 2 gates (fastest, ground-dominated)
       to track changing ground amplitude */
    for (int i = 0; i < 2; i++) {
        float residual = gates[i] - ground_model[i];
        /* If the residual is small (no target), update ground amplitude */
        if (fabsf(residual) < fabsf(ground_model[i]) * 0.3f) {
            float ref = expf(-GATE_DELAY_US[i] / g_ctx.ground_tau);
            g_ctx.ground_amp += mu * residual * ref;
            if (g_ctx.ground_amp < 0) g_ctx.ground_amp = 0;
        }
    }

    /* Subtract ground model from all gates */
    for (int i = 0; i < NUM_GATES; i++) {
        gates[i] -= ground_model[i];
        /* Clamp to non-negative (decay is always positive) */
        if (gates[i] < 0) gates[i] = 0;
    }
}