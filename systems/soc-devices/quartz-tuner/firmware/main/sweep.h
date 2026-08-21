/*
 * sweep.h — π-network frequency sweep orchestration
 *
 * Coordinates the Si5351A stimulus and AD5933 response measurement
 * to perform a complete frequency sweep across the crystal's
 * resonance region.
 */

#ifndef QUARTZ_TUNER_SWEEP_H
#define QUARTZ_TUNER_SWEEP_H

#include "types.h"

/* Run a complete frequency sweep centered on f_center with given span.
 * The Si5351A steps through 512 frequency points, and the AD5933
 * measures the complex admittance at each point.
 * Results are stored in the sweep_t structure.
 * Returns 0 on success, -1 on error. */
int sweep_run(sweep_t *sweep, float f_center_hz, float span_hz, uint16_t n_points);

/* Run a single-point measurement at a specific frequency.
 * Useful for real-time tracking of resonance during temperature sweep. */
int sweep_single_point(sweep_t *sweep, float freq_hz, const calibration_t *cal);

#endif /* QUARTZ_TUNER_SWEEP_H */