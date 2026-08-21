/*
 * calibration.c — PSL sphere calibration
 *
 * Fits peak_mV = A * d^B via log-log linear regression on the
 * calibration points, then generates bin boundaries.
 */

#include "calibration.h"
#include "pulse.h"
#include <math.h>
#include <string.h>

static calib_point_t points[CALIB_MAX_POINTS];
static uint8_t   point_count = 0;
static float     fit_A = 1.0f;
static float     fit_B = 2.0f;
static bool      done = false;

static uint32_t calib_counts = 0;
static float    calib_size = 0.0f;

/* Default bin edges in µm */
static const float default_edges[DEFAULT_BIN_COUNT + 1] = {
    0.30f, 0.40f, 0.50f, 0.70f, 1.00f, 1.30f, 1.70f, 2.20f,
    3.00f, 4.00f, 5.00f, 7.00f, 10.0f, 15.0f, 20.0f, 30.0f,
    40.0f
};

void calibration_init(void)
{
    point_count = 0;
    done = false;
    fit_A = 1.0f;
    fit_B = 2.0f;
    /* Generate default boundaries from default fit */
    float b[DEFAULT_BIN_COUNT + 1];
    calibration_get_boundaries_mv(b, NULL);
    pulse_set_boundaries(b, DEFAULT_BIN_COUNT + 1);
}

void calibration_start(void)
{
    calib_counts = 0;
    calib_size = 0.0f;
}

void calibration_finish(void)
{
    if (point_count >= 2) {
        /* Log-log linear regression: ln(V) = ln(A) + B·ln(d) */
        double Sx = 0, Sy = 0, Sxx = 0, Sxy = 0;
        for (uint8_t i = 0; i < point_count; ++i) {
            double x = log(points[i].size_um);
            double y = log(points[i].peak_mv);
            Sx += x; Sy += y;
            Sxx += x * x; Sxy += x * y;
        }
        double n = (double)point_count;
        double denom = n * Sxx - Sx * Sx;
        if (fabs(denom) > 1e-12) {
            fit_B = (float)((n * Sxy - Sx * Sy) / denom);
            fit_A = (float)exp((Sy - fit_B * Sx) / n);
        }
    }
    done = true;

    /* Update pulse boundaries from fit */
    float b[DEFAULT_BIN_COUNT + 1];
    calibration_get_boundaries_mv(b, NULL);
    pulse_set_boundaries(b, DEFAULT_BIN_COUNT + 1);
}

bool calibration_add_point(float size_um, float median_peak_mv)
{
    if (point_count >= CALIB_MAX_POINTS) return false;
    points[point_count].size_um = size_um;
    points[point_count].peak_mv = median_peak_mv;
    point_count++;
    return true;
}

float calibration_size_for_mv(float peak_mv)
{
    if (peak_mv <= 0 || fit_A <= 0) return 0.0f;
    return powf(peak_mv / fit_A, 1.0f / fit_B);
}

float calibration_mv_for_size(float size_um)
{
    if (size_um <= 0) return 0.0f;
    return fit_A * powf(size_um, fit_B);
}

void calibration_get_points(calib_point_t *out, uint8_t *count)
{
    if (count) *count = point_count;
    memcpy(out, points, point_count * sizeof(calib_point_t));
}

bool calibration_done(void) { return done; }
uint32_t calibration_counts(void) { return calib_counts; }
float calibration_current_size(void) { return calib_size; }

void calibration_get_bin_edges(float *edges, uint8_t *count)
{
    memcpy(edges, default_edges, sizeof(default_edges));
    if (count) *count = DEFAULT_BIN_COUNT + 1;
}

void calibration_get_boundaries_mv(float *boundaries, uint8_t *count)
{
    for (uint8_t i = 0; i <= DEFAULT_BIN_COUNT; ++i) {
        boundaries[i] = calibration_mv_for_size(default_edges[i]);
    }
    if (count) *count = DEFAULT_BIN_COUNT + 1;
}