/*
 * drude.c — Drude optical rotatory dispersion analysis
 * Opti Rot — Pocket Digital Polarimeter
 *
 * The Drude equation relates specific rotation to wavelength:
 *
 *   [α](λ) = K / (λ² - λ₀²)
 *
 * where K is a strength constant and λ₀ is the wavelength of a nearby
 * electronic absorption band. By measuring rotation at multiple
 * wavelengths, we can fit K and λ₀, providing a fingerprint of the
 * chiral compound that goes beyond single-wavelength rotation.
 *
 * Linearization: 1/[α] = (λ² - λ₀²)/K = λ²/K - λ₀²/K
 * Plot 1/[α] vs λ² → linear with slope = 1/K, intercept = -λ₀²/K
 * → K = 1/slope, λ₀ = sqrt(-intercept × K)
 *
 * With exactly 3 points we can solve analytically (any pair gives K, λ₀).
 * We use all pairs and average for robustness.
 */
#include <math.h>
#include "drude.h"

drude_result_t drude_fit(const double *alphas, const double *lambdas, int n)
{
    drude_result_t result = {0};

    if (n < 2) {
        result.valid = false;
        return result;
    }

    /* Linear regression: y = 1/[α], x = λ²
     * y = (1/K)·x - (λ₀²/K)
     * slope = 1/K, intercept = -λ₀²/K
     */
    double sum_x = 0, sum_y = 0, sum_xx = 0, sum_xy = 0;
    int count = 0;

    for (int i = 0; i < n; i++) {
        if (fabs(alphas[i]) < 1e-9)  /* skip near-zero rotations */
            continue;
        double x = lambdas[i] * lambdas[i];
        double y = 1.0 / alphas[i];
        sum_x  += x;
        sum_y  += y;
        sum_xx += x * x;
        sum_xy += x * y;
        count++;
    }

    if (count < 2) {
        result.valid = false;
        return result;
    }

    double denom = (double)count * sum_xx - sum_x * sum_x;
    if (fabs(denom) < 1e-18) {
        result.valid = false;
        return result;
    }

    double slope     = ((double)count * sum_xy - sum_x * sum_y) / denom;
    double intercept = (sum_y - slope * sum_x) / (double)count;

    if (fabs(slope) < 1e-18) {
        result.valid = false;
        return result;
    }

    result.K = 1.0 / slope;

    double intercept_times_K = intercept * result.K;
    if (intercept_times_K >= 0) {
        /* λ₀² would be negative — physically impossible for real Drude.
         * This can happen if the compound's absorption band is far from
         * the measurement range. Clamp to a small value. */
        result.lambda0_nm = 0.0;  /* no nearby absorption in measured range */
    } else {
        result.lambda0_nm = sqrt(-intercept_times_K);
    }

    /* Compute residual */
    double residual = 0;
    for (int i = 0; i < n; i++) {
        if (fabs(alphas[i]) < 1e-9)
            continue;
        double predicted = drude_predict(result.K, result.lambda0_nm, lambdas[i]);
        double diff = predicted - alphas[i];
        residual += diff * diff;
    }
    result.residual = residual;
    result.valid = true;

    return result;
}

double drude_predict(double K, double lambda0, double wavelength_nm)
{
    double denom = wavelength_nm * wavelength_nm - lambda0 * lambda0;
    if (fabs(denom) < 1e-6)
        return 0.0;
    return K / denom;
}