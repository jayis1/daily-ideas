/**
 * edge_detect.h — Bright/dark boundary detection for CCD waveforms
 *
 * Finds the critical-angle TIR shadow edge in the 256-pixel CCD output.
 * The boundary is a sharp transition from bright (totally reflected)
 * to dark (light transmitted into the sample). Sub-pixel refinement
 * via linear interpolation of the derivative peak gives ±0.1 pixel
 * resolution.
 */

#ifndef EDGE_DETECT_H
#define EDGE_DETECT_H

#include <stdint.h>

/**
 * Find the bright/dark boundary position in a CCD waveform.
 *
 * @param pixels   256-element array of CCD pixel values (dark-subtracted)
 * @param n        Number of pixels (typically 256)
 * @return         Sub-pixel boundary position (float pixel index)
 *                 Returns -1.0f if no boundary found
 */
float edge_detect_find_boundary(const uint16_t *pixels, int n);

/**
 * Compute the first derivative of the waveform.
 * Uses 5-tap central difference for noise rejection.
 *
 * @param pixels   Input waveform
 * @param deriv    Output derivative (n-4 elements valid)
 * @param n        Number of pixels
 */
void edge_detect_derivative(const uint16_t *pixels, float *deriv, int n);

/**
 * Compute a smoothed version of the waveform.
 * 5-tap moving average.
 */
void edge_detect_smooth(const uint16_t *pixels, float *smoothed, int n);

#endif /* EDGE_DETECT_H */