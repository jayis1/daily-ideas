/**
 * edge_detect.c — Bright/dark boundary detection
 *
 * The critical-angle TIR shadow edge appears as a step function on the
 * CCD: bright pixels (total internal reflection) on one side, dark pixels
 * (light transmitted into sample) on the other.
 *
 * Detection algorithm:
 *   1. Smooth with 5-tap moving average
 *   2. Compute first derivative (5-tap central difference)
 *   3. Find the steepest negative-going zero crossing
 *   4. Sub-pixel refine via linear interpolation between the two
 *      pixels straddling the derivative minimum
 */

#include "edge_detect.h"
#include <stdlib.h>
#include <math.h>

void edge_detect_smooth(const uint16_t *pixels, float *smoothed, int n) {
    for (int i = 0; i < n; i++) {
        float sum = 0;
        int count = 0;
        for (int k = -2; k <= 2; k++) {
            int idx = i + k;
            if (idx >= 0 && idx < n) {
                sum += (float)pixels[idx];
                count++;
            }
        }
        smoothed[i] = sum / count;
    }
}

void edge_detect_derivative(const uint16_t *pixels, float *deriv, int n) {
    /* 5-tap central difference derivative:
     * d[i] = (-p[i+2] + 8*p[i+1] - 8*p[i-1] + p[i-2]) / 12
     * (Lanczos kernel, 4th-order accurate)
     */
    for (int i = 2; i < n - 2; i++) {
        deriv[i] = (-(float)pixels[i + 2] + 8.0f * (float)pixels[i + 1]
                     - 8.0f * (float)pixels[i - 1] + (float)pixels[i - 2]) / 12.0f;
    }
    /* Edge cases — use simple forward/backward difference */
    if (n > 1) {
        deriv[0] = (float)pixels[1] - (float)pixels[0];
        deriv[1] = ((float)pixels[2] - (float)pixels[0]) / 2.0f;
        deriv[n - 2] = ((float)pixels[n - 1] - (float)pixels[n - 3]) / 2.0f;
        deriv[n - 1] = (float)pixels[n - 1] - (float)pixels[n - 2];
    }
}

float edge_detect_find_boundary(const uint16_t *pixels, int n) {
    if (!pixels || n < 10) return -1.0f;

    /* Step 1: Smooth */
    float *smoothed = (float *)malloc(n * sizeof(float));
    if (!smoothed) return -1.0f;
    edge_detect_smooth(pixels, smoothed, n);

    /* Step 2: Compute derivative */
    float *deriv = (float *)malloc(n * sizeof(float));
    if (!deriv) { free(smoothed); return -1.0f; }
    edge_detect_derivative((const uint16_t *)pixels, deriv, n);
    /* Recompute derivative on smoothed data for noise rejection */
    for (int i = 2; i < n - 2; i++) {
        deriv[i] = (-smoothed[i + 2] + 8.0f * smoothed[i + 1]
                     - 8.0f * smoothed[i - 1] + smoothed[i - 2]) / 12.0f;
    }

    /* Step 3: Find the steepest negative derivative (bright → dark) */
    float min_deriv = 0;
    int min_idx = -1;

    /* Search in the central region (avoid edge artifacts) */
    for (int i = 20; i < n - 20; i++) {
        if (deriv[i] < min_deriv) {
            min_deriv = deriv[i];
            min_idx = i;
        }
    }

    if (min_idx < 0 || min_deriv > -50.0f) {
        /* No significant edge found */
        free(smoothed);
        free(deriv);
        return -1.0f;
    }

    /* Step 4: Sub-pixel refinement via parabolic interpolation
     * Fit a parabola to the 3 points around the derivative minimum:
     *   y = a*x² + b*x + c
     *   x_min = -b / (2a) = 0.5*(d[i-1] - d[i+1]) / (d[i-1] - 2*d[i] + d[i+1])
     */
    float d_left = deriv[min_idx - 1];
    float d_center = deriv[min_idx];
    float d_right = deriv[min_idx + 1];

    float denom = d_left - 2.0f * d_center + d_right;
    float sub_pixel_offset = 0.0f;
    if (fabsf(denom) > 1e-6f) {
        sub_pixel_offset = 0.5f * (d_left - d_right) / denom;
    }

    float edge_pos = (float)min_idx + sub_pixel_offset;

    free(smoothed);
    free(deriv);

    return edge_pos;
}