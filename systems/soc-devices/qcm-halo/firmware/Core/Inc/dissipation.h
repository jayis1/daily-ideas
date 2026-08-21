/*
 * dissipation.h — Ring-down dissipation fitting
 */

#ifndef DISSIPATION_H
#define DISSIPATION_H

#include "config.h"

/* Fit exponential decay to ring-down samples → D
 *
 * A(t) = A0 * exp(-t / tau)
 * D = 1 / (pi * f0 * tau)
 *
 * Uses log-linear regression for initial estimate, then
 * Levenberg-Marquardt refinement for accuracy.
 */
float dissipation_fit(const uint16_t *samples, uint16_t n,
                      uint32_t sample_rate_hz, float f0_hz);

/* Quick estimate (log-linear only, faster) */
float dissipation_quick(const uint16_t *samples, uint16_t n,
                        uint32_t sample_rate_hz, float f0_hz);

/* Find decay start (skip first samples before TX fully off) */
uint16_t dissipation_find_start(const uint16_t *samples, uint16_t n);

#endif /* DISSIPATION_H */