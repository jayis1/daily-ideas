/*
 * calibration.h — PSL sphere calibration: pulse-height → particle size
 *
 * The device is calibrated using NIST-traceable polystyrene latex (PSL)
 * spheres of known diameters (e.g., 0.5, 1.0, 2.0, 5.0 µm). For each
 * size, the device records the peak-height distribution and finds the
 * median. The resulting (size_um, peak_mV) pairs are fit to a power law:
 *
 *     peak_mV = A * d^B
 *
 * (Mie theory predicts approximately V ∝ d^2 for geometric scattering
 * regime and V ∝ d^3 for Rayleigh, with oscillations; the power-law
 * fit captures the average trend.) The boundaries table maps the 16
 * size bins to pulse-height thresholds via this fit.
 *
 * Default bin edges (µm):
 *   0.30, 0.40, 0.50, 0.70, 1.00, 1.30, 1.70, 2.20, 3.00, 4.00,
 *   5.00, 7.00, 10.0, 15.0, 20.0, 30.0
 */

#ifndef CALIBRATION_H
#define CALIBRATION_H

#include <stdint.h>
#include <stdbool.h>

#define CALIB_MAX_POINTS   8
#define DEFAULT_BIN_COUNT   16

typedef struct {
    float size_um;
    float peak_mv;
} calib_point_t;

void   calibration_init(void);
void   calibration_start(void);
void   calibration_finish(void);
bool   calibration_add_point(float size_um, float median_peak_mv);
float  calibration_size_for_mv(float peak_mv);   /* inverse fit: mV → µm */
float  calibration_mv_for_size(float size_um);    /* forward fit: µm → mV */
void   calibration_get_points(calib_point_t *out, uint8_t *count);

/* Current calibration status */
bool   calibration_done(void);
uint32_t calibration_counts(void);
float  calibration_current_size(void);

/* Get the bin-edge diameters (µm) */
void   calibration_get_bin_edges(float *edges, uint8_t *count);

/* Get the pulse-height boundaries (mV) corresponding to the bin edges */
void   calibration_get_boundaries_mv(float *boundaries, uint8_t *count);

#endif /* CALIBRATION_H */