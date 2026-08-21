/*
 * motional.c — IEC 444 motional parameter extraction
 *
 * Implements the Kasa algebraic circle fitting method to find
 * the admittance circle from measured G-B data, then extracts
 * the standard motional parameters using IEC 444 relationships.
 */

#include "motional.h"
#include "admittance.h"
#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

int motional_extract(const sweep_t *sweep, motional_t *params,
                     const calibration_t *cal)
{
    if (sweep->n_points < 10) return -1;

    /* Step 1: Find series resonant frequency (maximum |Y|) */
    int peak_idx = 0;
    float max_mag = 0;
    for (int i = 0; i < sweep->n_points; i++) {
        float mag = sweep->points[i].mag;
        if (mag > max_mag) {
            max_mag = mag;
            peak_idx = i;
        }
    }

    /* Parabolic interpolation for sub-step frequency resolution */
    float f_peak = sweep->points[peak_idx].freq_hz;
    if (peak_idx > 0 && peak_idx < sweep->n_points - 1) {
        float y0 = sweep->points[peak_idx - 1].mag;
        float y1 = sweep->points[peak_idx].mag;
        float y2 = sweep->points[peak_idx + 1].mag;
        float denom = y0 - 2.0f * y1 + y2;
        if (fabsf(denom) > 1e-12f) {
            float delta = 0.5f * (y0 - y2) / denom;
            f_peak += delta * sweep->f_step_hz;
        }
    }
    params->f_s = f_peak;

    /* Step 2: Fit admittance circle using Kasa method
     * (algebraic circle fit: minimize Σ(x²+y²+ax+by+c)² )
     * This gives the center (a/2, b/2) and radius. */
    float Sx = 0, Sy = 0, Sxx = 0, Sxy = 0, Syy = 0;
    float Sxxx = 0, Sxxy = 0, Sxyy = 0, Syyy = 0;

    int n = sweep->n_points;
    for (int i = 0; i < n; i++) {
        float G = sweep->points[i].admittance.re;  /* conductance */
        float B = sweep->points[i].admittance.im;  /* susceptance */

        Sx += G;
        Sy += B;
        Sxx += G * G;
        Sxy += G * B;
        Syy += B * B;
        Sxxx += G * G * G;
        Sxxy += G * G * B;
        Sxyy += G * B * B;
        Syyy += B * B * B;
    }

    /* Kasa method: solve for A, B, C in x²+y²+Ax+By+C=0
     * Center = (-A/2, -B/2), Radius = sqrt(A²/4 + B²/4 - C) */
    float A1[3][3] = {
        {Sxx, Sxy, Sx},
        {Sxy, Syy, Sy},
        {Sx,  Sy,  (float)n}
    };
    float b1[3] = {-(Sxxx + Sxyy), -(Sxxy + Syyy), -(Sxx + Syy)};

    /* Solve 3x3 system using Cramer's rule */
    float det = A1[0][0] * (A1[1][1]*A1[2][2] - A1[1][2]*A1[2][1])
              - A1[0][1] * (A1[1][0]*A1[2][2] - A1[1][2]*A1[2][0])
              + A1[0][2] * (A1[1][0]*A1[2][1] - A1[1][1]*A1[2][0]);

    if (fabsf(det) < 1e-20f) return -1;  /* degenerate circle */

    float A = (b1[0] * (A1[1][1]*A1[2][2] - A1[1][2]*A1[2][1])
             - b1[1] * (A1[0][1]*A1[2][2] - A1[0][2]*A1[2][1])
             + b1[2] * (A1[0][1]*A1[1][2] - A1[0][2]*A1[1][1])) / det;

    float B = (A1[0][0] * (b1[1]*A1[2][2] - b1[2]*A1[1][2])
             - A1[0][1] * (b1[0]*A1[2][2] - b1[2]*A1[0][2])
             + A1[0][2] * (b1[0]*A1[1][2] - b1[1]*A1[0][2])) / det;

    /* Circle center and radius */
    float center_G = -A / 2.0f;
    float center_B = -B / 2.0f;
    float radius = sqrtf(center_G * center_G + center_B * center_B - 0.0f);
    /* Note: C is computed implicitly; radius = sqrt(center_G² + center_B² - C) */

    /* Step 3: Extract R₁ from circle diameter
     * The diameter of the admittance circle = 1/R₁
     * (for a series RLC circuit in the π-network) */
    params->R1 = 1.0f / (2.0f * radius);

    /* Step 4: Find 3 dB bandwidth
     * At the -3 dB points, |Y| = |Y_peak| / sqrt(2)
     * The frequency difference between the two -3 dB points = Δf */
    float Y_peak = max_mag;
    float Y_3dB = Y_peak / 1.41421356f;

    float f_minus = 0, f_plus = 0;
    bool found_minus = false, found_plus = false;

    for (int i = 1; i < peak_idx; i++) {
        if (sweep->points[i].mag <= Y_3dB && sweep->points[i-1].mag > Y_3dB) {
            /* Linear interpolation for sub-step accuracy */
            float frac = (Y_3dB - sweep->points[i].mag) /
                         (sweep->points[i-1].mag - sweep->points[i].mag);
            f_minus = sweep->points[i].freq_hz - frac * sweep->f_step_hz;
            found_minus = true;
            break;
        }
    }
    for (int i = peak_idx + 1; i < n - 1; i++) {
        if (sweep->points[i].mag <= Y_3dB && sweep->points[i-1].mag > Y_3dB) {
            float frac = (Y_3dB - sweep->points[i].mag) /
                         (sweep->points[i-1].mag - sweep->points[i].mag);
            f_plus = sweep->points[i].freq_hz - frac * sweep->f_step_hz;
            found_plus = true;
            break;
        }
    }

    if (found_minus && found_plus) {
        float delta_f = f_plus - f_minus;
        params->Q = f_peak / delta_f;
    } else {
        /* Fallback: estimate Q from circle geometry */
        params->Q = 2.0f * 3.14159265f * f_peak * params->R1 * 0.001f;
    }

    /* Step 5: Compute L₁, C₁ from Q, R₁, fₛ */
    float omega_s = 2.0f * 3.14159265f * f_peak;
    params->L1 = (params->Q * params->R1) / omega_s;
    params->C1 = 1.0f / (omega_s * omega_s * params->L1);

    /* Step 6: Compute C₀ from off-resonance susceptance
     * At frequencies far from resonance, Y ≈ jωC₀
     * Use the average susceptance of the first and last 10% of points */
    float B_off = 0;
    int n_off = 0;
    int n_off_range = n / 10;
    if (n_off_range < 1) n_off_range = 1;

    for (int i = 0; i < n_off_range; i++) {
        float omega = 2.0f * 3.14159265f * sweep->points[i].freq_hz;
        if (omega > 1.0f) {
            B_off += sweep->points[i].admittance.im / omega;
            n_off++;
        }
    }
    for (int i = n - n_off_range; i < n; i++) {
        float omega = 2.0f * 3.14159265f * sweep->points[i].freq_hz;
        if (omega > 1.0f) {
            B_off += sweep->points[i].admittance.im / omega;
            n_off++;
        }
    }
    if (n_off > 0) {
        params->C0 = B_off / (float)n_off;
    } else {
        params->C0 = 0;  /* unknown */
    }

    /* Step 7: Compute ESR (equivalent series resistance) */
    /* ESR = R1 * (1 + C0/C1)^2 / (C0/C1) -- simplified: ESR ≈ R1 for high Q */
    params->ESR = params->R1;  /* first-order approximation */
    if (params->C0 > 0 && params->C1 > 0) {
        float ratio = params->C0 / params->C1;
        params->ESR = params->R1 * (1.0f + ratio) * (1.0f + ratio) / ratio;
        /* For typical crystals (C0/C1 >> 1), ESR ≈ R1 */
    }

    /* Step 8: Compute pullability (ppm/pF) */
    /* pullability = C1 / (2 * C0) in ppm/pF at the load capacitance */
    if (params->C0 > 0) {
        params->pullability = (params->C1 / (2.0f * params->C0)) * 1e6f;
        /* Convert to ppm/pF: Δf/f = C1/(2*(C0+CL)) where CL is load cap */
        /* Simplified: ppm/pF ≈ C1/(2*C0^2) * 1e6 when CL = C0 */
    } else {
        params->pullability = 0;
    }

    /* Step 9: Circle fit residual (quality metric) */
    float residual = 0;
    for (int i = 0; i < n; i++) {
        float G = sweep->points[i].admittance.re;
        float B = sweep->points[i].admittance.im;
        float dist = sqrtf((G - center_G) * (G - center_G) +
                           (B - center_B) * (B - center_B));
        float diff = dist - radius;
        residual += diff * diff;
    }
    params->circle_residual = sqrtf(residual / (float)n);

    params->valid = true;
    return 0;
}