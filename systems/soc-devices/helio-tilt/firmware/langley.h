/*
 * langley.h — Langley calibration regression
 */

#ifndef LANGLEY_H
#define LANGLEY_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float v0[6];          /* Extraterrestrial constants V₀(λ) per wavelength */
    float tau_total[6];   /* Total optical depth from regression slope */
    float r_squared[6];   /* Regression R² per wavelength (quality metric) */
    uint16_t num_points;  /* Number of data points used */
    bool   valid;         /* True if R² > LANGLEY_MIN_R2 for all wavelengths */
} langley_result_t;

/* Add a Langley data point (voltage per wavelength + air mass).
 * Called periodically during a Langley calibration run.
 */
void langley_add_point(const float voltages_uv[6], double air_mass);

/* Run linear regression: ln(V) = ln(V₀) - τ × m
 * Computes V₀, τ, and R² for each wavelength.
 */
void langley_regress(langley_result_t *result);

/* Reset Langley buffer for a new calibration run */
void langley_reset(void);

/* Check if enough points collected */
bool langley_ready(void);

/* Get current point count */
uint16_t langley_point_count(void);

#endif /* LANGLEY_H */