/*
 * admittance.h — Admittance circle fitting (Kasa method)
 *
 * Fits the measured complex admittance data to a circle
 * in the G-B plane using the algebraic Kasa method.
 * Used by motional.c for parameter extraction.
 */

#ifndef QUARTZ_TUNER_ADMITTANCE_H
#define QUARTZ_TUNER_ADMITTANCE_H

#include "types.h"

/* Fit result: circle center, radius, and residual */
typedef struct {
    float center_G;     /* center conductance (S) */
    float center_B;     /* center susceptance (S) */
    float radius;       /* circle radius (S) */
    float residual;      /* RMS residual of fit (S) */
    bool valid;
} circle_fit_t;

/* Fit admittance data to a circle using the Kasa method.
 * Returns the circle center, radius, and residual. */
int admittance_circle_fit(const sweep_t *sweep, circle_fit_t *result);

/* Compute the distance of a point from the fitted circle.
 * Useful for outlier rejection. */
float admittance_circle_distance(const circle_fit_t *fit, complex_t point);

#endif /* QUARTZ_TUNER_ADMITTANCE_H */