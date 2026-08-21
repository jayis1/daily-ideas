/*
 * turnover.h — Temperature turnover curve measurement
 *
 * Drives a resistive heater around the crystal and measures
 * the frequency shift vs. temperature, fitting a 3rd-order
 * polynomial: Δf/f₀(T) = a₀ + a₁(T-T₀) + a₂(T-T₀)² + a₃(T-T₀)³
 */

#ifndef QUARTZ_TUNER_TURNOVER_H
#define QUARTZ_TUNER_TURNOVER_H

#include "types.h"

/* Run a temperature sweep from current temperature to target_max.
 * Heats the crystal using the MOSFET-driven resistor while tracking
 * series resonance with the Si5351A + AD5933. */
int turnover_sweep(turnover_t *turnover, sweep_t *sweep,
                  const calibration_t *cal);

/* Fit a 3rd-order polynomial to the turnover curve data.
 * Returns the turnover temperature T₀ and coefficients a₀-a₃. */
int turnover_fit(turnover_t *turnover);

#endif /* QUARTZ_TUNER_TURNOVER_H */