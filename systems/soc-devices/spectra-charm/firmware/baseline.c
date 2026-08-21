/*
 * Spectra Charm — Pocket UV-Vis Spectrophotometer
 * baseline.c — Spectral baseline correction (scattering removal)
 *
 * Fits and subtracts a polynomial baseline to correct for
 * Rayleigh scattering and instrumental drift.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "baseline.h"
#include <math.h>
#include <string.h>

/*
 * Baseline_Correct — Remove baseline drift and scattering
 *
 * Uses iterative polynomial fitting (modified least-squares):
 * 1. Fit a 3rd-order polynomial to the spectrum
 * 2. Iteratively: reject points above the fit (they're peaks)
 * 3. Refit to remaining points
 * 4. Subtract the resulting baseline
 *
 * This is a simplified version of the asymmetric least squares
 * smoothing (ALS) baseline correction algorithm.
 */
void Baseline_Correct(float absorbance[SPECTRUM_POINTS])
{
    float baseline[SPECTRUM_POINTS];
    float weights[SPECTRUM_POINTS];
    float x[SPECTRUM_POINTS];

    /* Initialize weights to 1.0 */
    for (int i = 0; i < SPECTRUM_POINTS; i++) {
        weights[i] = 1.0f;
        x[i] = (float)i;
    }

    /* Iterative asymmetric least squares (5 iterations) */
    for (int iter = 0; iter < 5; iter++) {
        /* Weighted polynomial fit (3rd order) using normal equations */
        /* S = sum(w_i * x_i^j * x_i^k) for j,k in [0..3] */
        float A[4][4] = {0};
        float b[4] = {0};

        for (int i = 0; i < SPECTRUM_POINTS; i++) {
            float w = weights[i];
            float xi = x[i];
            float yi = absorbance[i];

            float xpow[5] = {1.0f, xi, xi*xi, xi*xi*xi, xi*xi*xi*xi};
            for (int j = 0; j < 4; j++) {
                b[j] += w * xpow[j] * yi;
                for (int k = 0; k < 4; k++) {
                    A[j][k] += w * xpow[j+k];
                }
            }
        }

        /* Solve 4x4 system via Gaussian elimination */
        float coeff[4] = {0};
        for (int col = 0; col < 4; col++) {
            /* Partial pivoting */
            int maxrow = col;
            float maxval = fabsf(A[col][col]);
            for (int row = col + 1; row < 4; row++) {
                if (fabsf(A[row][col]) > maxval) {
                    maxval = fabsf(A[row][col]);
                    maxrow = row;
                }
            }
            /* Swap rows */
            if (maxrow != col) {
                for (int k = 0; k < 4; k++) {
                    float tmp = A[col][k];
                    A[col][k] = A[maxrow][k];
                    A[maxrow][k] = tmp;
                }
                float tmp = b[col];
                b[col] = b[maxrow];
                b[maxrow] = tmp;
            }

            /* Elimination */
            for (int row = col + 1; row < 4; row++) {
                float factor = A[row][col] / A[col][col];
                for (int k = col; k < 4; k++) {
                    A[row][k] -= factor * A[col][k];
                }
                b[row] -= factor * b[col];
            }
        }

        /* Back-substitution */
        for (int row = 3; row >= 0; row--) {
            coeff[row] = b[row];
            for (int k = row + 1; k < 4; k++) {
                coeff[row] -= A[row][k] * coeff[k];
            }
            coeff[row] /= A[row][row];
        }

        /* Evaluate baseline polynomial */
        for (int i = 0; i < SPECTRUM_POINTS; i++) {
            float xi = x[i];
            baseline[i] = coeff[0] + coeff[1]*xi + coeff[2]*xi*xi + coeff[3]*xi*xi*xi;
        }

        /* Update weights — downweight points above baseline (peaks) */
        for (int i = 0; i < SPECTRUM_POINTS; i++) {
            float residual = absorbance[i] - baseline[i];
            if (residual > 0.0f) {
                weights[i] = 0.001f; /* Heavily downweight peaks */
            } else {
                weights[i] = 1.0f;
            }
        }
    }

    /* Subtract baseline from absorbance */
    for (int i = 0; i < SPECTRUM_POINTS; i++) {
        absorbance[i] -= baseline[i];
        if (absorbance[i] < 0.0f) absorbance[i] = 0.0f;
    }
}