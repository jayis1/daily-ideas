/**
 * noise_analyzer.h — Background noise analysis and NC curve estimation
 */

#ifndef NOISE_ANALYZER_H
#define NOISE_ANALYZER_H

#include <stdint.h>
#include "acoustic_params.h"

/**
 * Compute Noise Criteria (NC) curve from ambient noise capture.
 *
 * Captures 30 s of ambient noise, computes 1/3-octave band SPL
 * levels, and determines the NC rating.
 *
 * @param captured     Captured ambient noise (int16, left channel)
 * @param num_samples  Number of samples
 * @param sample_rate  Sample rate in Hz
 * @param results      Output: filled nc_bands and nc_rating fields
 * @return 0 on success
 */
int noise_analyzer_compute_nc(const int16_t *captured, uint32_t num_samples,
                                uint32_t sample_rate,
                                acoustic_results_t *results);

#endif /* NOISE_ANALYZER_H */