/*
 * admittance.c — Admittance circle fitting (Kasa method)
 */

#include "admittance.h"
#include <math.h>

int admittance_circle_fit(const sweep_t *sweep, circle_fit_t *result)
{
    if (sweep->n_points < 3) return -1;

    float Sx = 0, Sy = 0, Sxx = 0, Sxy = 0, Syy = 0;
    float Sxxx = 0, Sxxy = 0, Sxyy = 0, Syyy = 0;
    int n = sweep->n_points;

    for (int i = 0; i < n; i++) {
        float G = sweep->points[i].admittance.re;
        float B = sweep->points[i].admittance.im;
        Sx += G; Sy += B;
        Sxx += G*G; Sxy += G*B; Syy += B*B;
        Sxxx += G*G*G; Sxxy += G*G*B; Sxyy += G*B*B; Syyy += B*B*B;
    }

    /* Solve for A, B in: x²+y² + Ax + By + C = 0 */
    float det = Sxx*(Syy*n - Sy*Sy) - Sxy*(Sxy*n - Sx*Sy) + Sx*(Sxy*Sy - Syy*Sx);
    if (fabsf(det) < 1e-30f) return -1;

    float A_num = (Sxxx + Sxyy)*(Syy*n - Sy*Sy) - (Sxxy + Syyy)*(Sxy*n - Sx*Sy)
                + (Sxx + Syy)*(Sxy*Sy - Syy*Sx);
    float B_num = (Sxx + Syy)*(Sxy*n - Sx*Sy) - (Sxxx + Sxyy)*(Sxy*n - Sx*Sy)
                + (Sxxy + Syyy)*(Sxx*n - Sx*Sx);

    float A = A_num / det;
    float B = B_num / det;

    result->center_G = -A / 2.0f;
    result->center_B = -B / 2.0f;

    /* Compute radius from center */
    float sum_r2 = 0;
    for (int i = 0; i < n; i++) {
        float G = sweep->points[i].admittance.re;
        float B = sweep->points[i].admittance.im;
        float dx = G - result->center_G;
        float dy = B - result->center_B;
        sum_r2 += dx*dx + dy*dy;
    }
    result->radius = sqrtf(sum_r2 / (float)n);

    /* Compute residual */
    float residual = 0;
    for (int i = 0; i < n; i++) {
        float dist = admittance_circle_distance(result, sweep->points[i].admittance);
        residual += dist * dist;
    }
    result->residual = sqrtf(residual / (float)n);
    result->valid = true;

    return 0;
}

float admittance_circle_distance(const circle_fit_t *fit, complex_t point)
{
    float dx = point.re - fit->center_G;
    float dy = point.im - fit->center_B;
    float dist = sqrtf(dx*dx + dy*dy);
    return dist - fit->radius;
}