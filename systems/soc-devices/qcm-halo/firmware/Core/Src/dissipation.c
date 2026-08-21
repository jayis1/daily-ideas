/*
 * dissipation.c — Ring-down exponential fitting for QCM-D dissipation
 *
 * The QCM crystal is driven at resonance, then the drive is abruptly
 * disconnected. The oscillation decays exponentially:
 *
 *   A(t) = A0 * exp(-t / tau)
 *
 * The dissipation factor is:
 *   D = 1 / (pi * f0 * tau)
 *
 * We fit the decay using:
 *   1. Log-linear regression for initial tau estimate
 *   2. Levenberg-Marquardt refinement for accuracy
 */

#include "main.h"
#include <math.h>
#include <string.h>
#include "dissipation.h"

/* Find the start of the decay (skip samples before TX fully off).
 * Look for the peak amplitude, then start from there.
 */
uint16_t dissipation_find_start(const uint16_t *samples, uint16_t n)
{
    uint16_t peak_idx = 0;
    uint16_t peak_val = 0;

    /* Search first 10% of samples for peak */
    uint16_t search_end = n / 10;
    if (search_end < 10) search_end = n;

    for (uint16_t i = 0; i < search_end && i < n; i++) {
        if (samples[i] > peak_val) {
            peak_val = samples[i];
            peak_idx = i;
        }
    }

    /* Start a few samples after peak to avoid switching transient */
    uint16_t start = peak_idx + 3;
    if (start >= n) start = n - 1;
    return start;
}

/* Quick estimate using log-linear regression.
 * Takes the natural log of the envelope and fits a line.
 * tau = -1/slope
 */
float dissipation_quick(const uint16_t *samples, uint16_t n,
                        uint32_t sample_rate_hz, float f0_hz)
{
    uint16_t start = dissipation_find_start(samples, n);

    /* Convert to envelope: samples are centered at Vcc/2 ≈ 2048 for 12-bit.
     * Take absolute deviation from mid-point as the envelope amplitude.
     */
    const uint16_t mid = 2048;

    /* Use log of amplitude — need enough samples for a fit.
     * Take every Nth sample to reduce noise and computation.
     */
    uint16_t step = 1;
    if (n > 512) step = n / 256;

    float sum_x = 0, sum_y = 0, sum_xx = 0, sum_xy = 0;
    uint16_t count = 0;
    float dt = 1.0f / (float)sample_rate_hz;

    for (uint16_t i = start; i < n; i += step) {
        int32_t dev = (int32_t)samples[i] - (int32_t)mid;
        float amp = (float)(dev < 0 ? -dev : dev);
        if (amp < 1.0f) amp = 1.0f; /* avoid log(0) */

        float t = (float)(i - start) * dt;
        float y = logf(amp);

        sum_x  += t;
        sum_y  += y;
        sum_xx += t * t;
        sum_xy += t * y;
        count++;
    }

    if (count < 3) return 0.0f;

    /* Linear regression: y = a + b*t, where b = -1/tau */
    float denom = (float)count * sum_xx - sum_x * sum_x;
    if (fabsf(denom) < 1e-20f) return 0.0f;

    float b = ((float)count * sum_xy - sum_x * sum_y) / denom;

    if (fabsf(b) < 1e-20f) return 0.0f;

    float tau = -1.0f / b;
    if (tau <= 0) return 0.0f;

    float D = 1.0f / (PI * f0_hz * tau);
    return D;
}

/* Full Levenberg-Marquardt fit for higher accuracy.
 * Model: A(t) = A0 * exp(-t / tau) + offset
 * Parameters: [A0, tau, offset]
 */
float dissipation_fit(const uint16_t *samples, uint16_t n,
                      uint32_t sample_rate_hz, float f0_hz)
{
    uint16_t start = dissipation_find_start(samples, n);
    const uint16_t mid = 2048;
    float dt = 1.0f / (float)sample_rate_hz;

    /* Initial estimates from quick fit */
    float tau = -1.0f; /* will be set from quick estimate */

    /* Get initial A0 from first sample after start */
    int32_t dev0 = (int32_t)samples[start] - (int32_t)mid;
    float A0 = (float)(dev0 < 0 ? -dev0 : dev0);
    if (A0 < 1.0f) A0 = 1.0f;

    float offset = 0.0f;

    /* Quick log-linear for initial tau */
    {
        float sum_x = 0, sum_y = 0, sum_xx = 0, sum_xy = 0;
        uint16_t count = 0;
        uint16_t step = (n > 512) ? n / 256 : 1;

        for (uint16_t i = start; i < n; i += step) {
            int32_t dev = (int32_t)samples[i] - (int32_t)mid;
            float amp = (float)(dev < 0 ? -dev : dev);
            if (amp < 1.0f) amp = 1.0f;
            float t = (float)(i - start) * dt;
            float y = logf(amp);
            sum_x += t; sum_y += y;
            sum_xx += t * t; sum_xy += t * y;
            count++;
        }
        if (count >= 3) {
            float denom = (float)count * sum_xx - sum_x * sum_x;
            if (fabsf(denom) > 1e-20f) {
                float b = ((float)count * sum_xy - sum_x * sum_y) / denom;
                if (b < -1e-20f) tau = -1.0f / b;
            }
        }
    }

    if (tau <= 0) return 0.0f;

    /* Levenberg-Marquardt iteration */
    /* Parameters: p = [A0, tau, offset] */
    float p[3] = {A0, tau, offset};
    float lambda = 0.01f;
    uint16_t max_iter = 50;

    /* Use downsampled data for speed */
    uint16_t step = (n > 512) ? 4 : 1;
    uint16_t ndata = 0;
    for (uint16_t i = start; i < n; i += step) ndata++;
    if (ndata < 5) return 1.0f / (PI * f0_hz * tau);

    for (uint16_t iter = 0; iter < max_iter; iter++) {
        /* Compute residual and Jacobian */
        float J[3];
        float residual;
        float chi2 = 0;
        float grad[3] = {0, 0, 0};
        float hess[3][3] = {{0,0,0},{0,0,0},{0,0,0}};

        for (uint16_t i = start, k = 0; i < n; i += step, k++) {
            float t = (float)(i - start) * dt;
            float expval = expf(-t / p[1]);
            float model = p[0] * expval + p[2];

            int32_t dev = (int32_t)samples[i] - (int32_t)mid;
            float amp = (float)(dev < 0 ? -dev : dev);
            residual = amp - model;
            chi2 += residual * residual;

            /* Jacobian: d(model)/dA0 = expval
             *           d(model)/dtau = p[0] * t / p[1]^2 * expval
             *           d(model)/doffset = 1
             */
            J[0] = expval;
            J[1] = p[0] * t / (p[1] * p[1]) * expval;
            J[2] = 1.0f;

            for (int a = 0; a < 3; a++) {
                grad[a] += J[a] * residual;
                for (int b = 0; b < 3; b++) {
                    hess[a][b] += J[a] * J[b];
                }
            }
        }

        /* Check convergence */
        if (chi2 < 1.0f) break;

        /* Augment Hessian with lambda */
        for (int a = 0; a < 3; a++)
            hess[a][a] *= (1.0f + lambda);

        /* Solve 3x3 normal equations (Gaussian elimination) */
        float aug[3][4];
        for (int a = 0; a < 3; a++) {
            for (int b = 0; b < 3; b++)
                aug[a][b] = hess[a][b];
            aug[a][3] = grad[a];
        }

        /* Forward elimination */
        for (int a = 0; a < 3; a++) {
            if (fabsf(aug[a][a]) < 1e-20f) continue;
            for (int b = a + 1; b < 3; b++) {
                float factor = aug[b][a] / aug[a][a];
                for (int c = a; c <= 3; c++)
                    aug[b][c] -= factor * aug[a][c];
            }
        }

        /* Back substitution */
        float dp[3] = {0, 0, 0};
        for (int a = 2; a >= 0; a--) {
            dp[a] = aug[a][3];
            for (int b = a + 1; b < 3; b++)
                dp[a] -= aug[a][b] * dp[b];
            if (fabsf(aug[a][a]) > 1e-20f)
                dp[a] /= aug[a][a];
        }

        /* Update parameters (with damping check) */
        float new_p[3] = {p[0] + dp[0], p[1] + dp[1], p[2] + dp[2]};

        /* Ensure tau stays positive */
        if (new_p[1] <= 0) new_p[1] = p[1] * 0.5f;
        if (new_p[0] < 0) new_p[0] = p[0];

        /* Compute new chi2 */
        float new_chi2 = 0;
        for (uint16_t i = start; i < n; i += step) {
            float t = (float)(i - start) * dt;
            int32_t dev = (int32_t)samples[i] - (int32_t)mid;
            float amp = (float)(dev < 0 ? -dev : dev);
            float model = new_p[0] * expf(-t / new_p[1]) + new_p[2];
            float r = amp - model;
            new_chi2 += r * r;
        }

        if (new_chi2 < chi2) {
            /* Accept step */
            p[0] = new_p[0]; p[1] = new_p[1]; p[2] = new_p[2];
            lambda *= 0.5f;
            if (lambda < 1e-6f) lambda = 1e-6f;
        } else {
            /* Reject step, increase lambda */
            lambda *= 10.0f;
            if (lambda > 1e6f) break;
        }
    }

    float D = 1.0f / (PI * f0_hz * p[1]);
    return D;
}