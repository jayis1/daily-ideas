/*
 * calibrate.c — OSLT calibration procedures
 *
 * Measures the four calibration standards (short, open, load, through)
 * and computes correction coefficients for the π-network fixture.
 */

#include "calibrate.h"
#include "ad5933.h"
#include "si5351.h"
#include <math.h>

static complex_t cal_short[SWEEP_POINTS_MAX];
static complex_t cal_open[SWEEP_POINTS_MAX];
static complex_t cal_load[SWEEP_POINTS_MAX];
static complex_t cal_through[SWEEP_POINTS_MAX];
static int cal_n_points = 0;

/* Run a single-frequency calibration measurement at the center frequency */
static int cal_measure(complex_t *result)
{
    complex_t raw;
    if (ad5933_measure_at_freq(0, &raw) != 0) return -1;
    *result = raw;
    return 0;
}

int calibrate_short(calibration_t *cal)
{
    (void)cal;
    return cal_measure(&cal_short[0]);
}

int calibrate_open(calibration_t *cal)
{
    (void)cal;
    return cal_measure(&cal_open[0]);
}

int calibrate_load(calibration_t *cal)
{
    (void)cal;
    /* Load standard is 50 Ω ±0.1% */
    complex_t load_raw;
    int rc = cal_measure(&load_raw);

    /* Compute system gain and phase from load standard */
    float mag = sqrtf(load_raw.re * load_raw.re + load_raw.im * load_raw.im);
    float phase = atan2f(load_raw.im, load_raw.re);

    /* Expected admittance of 50 Ω load: Y = 1/50 = 0.02 S */
    float Y_expected = 0.02f;
    cal->system_gain = Y_expected / mag;
    cal->system_phase = phase;

    return rc;
}

int calibrate_through(calibration_t *cal)
{
    (void)cal;
    return cal_measure(&cal_through[0]);
}