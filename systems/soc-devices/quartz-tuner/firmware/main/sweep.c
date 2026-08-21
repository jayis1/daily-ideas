/*
 * sweep.c — π-network frequency sweep orchestration
 *
 * Performs a stepped frequency sweep by coordinating the Si5351A
 * stimulus generator and AD5933 response receiver. At each frequency
 * point, the Si5351A sets the stimulus frequency, the AD5933
 * performs a DFT measurement, and the raw result is calibrated
 * and stored.
 */

#include "sweep.h"
#include "si5351.h"
#include "ad5933.h"
#include "calibrate.h"
#include <math.h>
#include <string.h>

/* Settle time between frequency steps (ms) */
#define SETTLE_MS    2

int sweep_run(sweep_t *sweep, float f_center_hz, float span_hz, uint16_t n_points)
{
    if (n_points > SWEEP_POINTS_MAX) return -1;

    sweep->f_center_hz = f_center_hz;
    sweep->span_hz = span_hz;
    sweep->f_start_hz = f_center_hz - span_hz / 2.0f;
    sweep->f_step_hz = span_hz / (float)n_points;
    sweep->timestamp_ms = HAL_GetTick();

    /* Start Si5351A sweep */
    uint32_t f_start = (uint32_t)sweep->f_start_hz;
    uint32_t f_stop = (uint32_t)(f_start + (uint32_t)span_hz);

    if (si5351_sweep_start(f_start, f_stop, n_points) != 0) return -1;

    /* Wait for initial settling */
    HAL_Delay(10);

    /* Step through frequencies */
    for (int i = 0; i < n_points; i++) {
        float freq = sweep->f_start_hz + i * sweep->f_step_hz;

        /* Set stimulus frequency */
        si5351_set_frequency((uint32_t)freq);

        /* Settle */
        HAL_Delay(SETTLE_MS);

        /* Measure response */
        complex_t raw, calibrated;
        if (ad5933_measure_at_freq((uint32_t)freq, &raw) != 0) {
            /* Skip failed measurements */
            sweep->points[i].freq_hz = freq;
            sweep->points[i].admittance.re = 0;
            sweep->points[i].admittance.im = 0;
            sweep->points[i].raw = raw;
            sweep->points[i].mag = 0;
            sweep->points[i].phase_deg = 0;
            continue;
        }

        /* Calibrate raw DFT to admittance */
        ad5933_to_admittance(&raw, &sweep->cal, &calibrated);

        /* Store result */
        sweep->points[i].freq_hz = freq;
        sweep->points[i].admittance = calibrated;
        sweep->points[i].raw = raw;
        sweep->points[i].mag = sqrtf(calibrated.re * calibrated.re +
                                      calibrated.im * calibrated.im);
        sweep->points[i].phase_deg = atan2f(calibrated.im, calibrated.re) *
                                      180.0f / 3.14159265f;
    }

    sweep->n_points = n_points;

    /* Find peak admittance (series resonance) */
    float max_mag = 0;
    int max_idx = 0;
    for (int i = 0; i < n_points; i++) {
        if (sweep->points[i].mag > max_mag) {
            max_mag = sweep->points[i].mag;
            max_idx = i;
        }
    }

    /* Refine center frequency around peak for next sweep */
    if (max_idx > 0 && max_idx < n_points - 1) {
        /* Parabolic interpolation for sub-step accuracy */
        float y0 = sweep->points[max_idx - 1].mag;
        float y1 = sweep->points[max_idx].mag;
        float y2 = sweep->points[max_idx + 1].mag;
        float delta = 0.5f * (y0 - y2) / (y0 - 2.0f * y1 + y2);
        sweep->f_center_hz = sweep->points[max_idx].freq_hz + delta * sweep->f_step_hz;
    }

    return 0;
}

int sweep_single_point(sweep_t *sweep, float freq_hz, const calibration_t *cal)
{
    complex_t raw, calibrated;

    si5351_set_frequency((uint32_t)freq_hz);
    HAL_Delay(SETTLE_MS);

    if (ad5933_measure_at_freq((uint32_t)freq_hz, &raw) != 0) return -1;

    ad5933_to_admittance(&raw, cal, &calibrated);

    /* Append to sweep */
    if (sweep->n_points < SWEEP_POINTS_MAX) {
        int i = sweep->n_points;
        sweep->points[i].freq_hz = freq_hz;
        sweep->points[i].admittance = calibrated;
        sweep->points[i].raw = raw;
        sweep->points[i].mag = sqrtf(calibrated.re * calibrated.re +
                                      calibrated.im * calibrated.im);
        sweep->points[i].phase_deg = atan2f(calibrated.im, calibrated.re) *
                                      180.0f / 3.14159265f;
        sweep->n_points++;
    }

    return 0;
}