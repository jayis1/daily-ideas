/*
 * motional.h — IEC 444 motional parameter extraction
 *
 * Extracts R₁, C₁, L₁, C₀, Q, and ESR from the measured
 * admittance circle using the Kasa circle fitting method
 * and the standard IEC 444 / π-network relationships.
 */

#ifndef QUARTZ_TUNER_MOTIONAL_H
#define QUARTZ_TUNER_MOTIONAL_H

#include "types.h"

/* Extract motional parameters from a completed sweep.
 * Uses the admittance circle (G-B plane) to find:
 *   R₁ = 1 / circle_diameter
 *   fₛ = frequency at maximum |Y|
 *   Q = fₛ / (3 dB bandwidth)
 *   L₁ = Q · R₁ / (2π · fₛ)
 *   C₁ = 1 / ((2π · fₛ)² · L₁)
 *   C₀ = off-resonance susceptance / (2π · fₛ)
 *
 * Returns 0 on success, -1 if fitting fails. */
int motional_extract(const sweep_t *sweep, motional_t *params,
                     const calibration_t *cal);

#endif /* QUARTZ_TUNER_MOTIONAL_H */