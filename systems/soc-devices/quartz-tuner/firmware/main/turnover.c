/*
 * turnover.c — Temperature turnover curve measurement and fitting
 *
 * Implements a PID-controlled heater to sweep crystal temperature
 * while tracking series resonance. Fits a 3rd-order polynomial
 * to extract the turnover temperature and frequency stability.
 */

#include "turnover.h"
#include "heater.h"
#include "si5351.h"
#include "sweep.h"
#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

int turnover_sweep(turnover_t *turnover, sweep_t *sweep,
                  const calibration_t *cal)
{
    turnover->n_points = 0;
    turnover->valid = false;

    /* Temperature sweep: heat from ambient to 80°C, then cool back.
     * Take a measurement every 2°C. */
    float temp_start = heater_read_temp();
    float temp_target = 80.0f;
    float temp_step = 2.0f;

    /* Phase 1: Heating */
    heater_set_target(temp_target);
    heater_enable(true);

    float last_temp = temp_start;
    while (heater_read_temp() < temp_target && turnover->n_points < TEMP_POINTS_MAX) {
        float current_temp = heater_read_temp();
        if (fabsf(current_temp - last_temp) >= temp_step) {
            /* Track series resonance at this temperature */
            /* Refine sweep around peak */
            sweep_single_point(sweep, sweep->f_center_hz, cal);

            /* Find peak */
            float f_s = 0;
            float max_mag = 0;
            for (int i = 0; i < sweep->n_points; i++) {
                if (sweep->points[i].mag > max_mag) {
                    max_mag = sweep->points[i].mag;
                    f_s = sweep->points[i].freq_hz;
                }
            }

            turnover->points[turnover->n_points].temp_c = current_temp;
            turnover->points[turnover->n_points].f_measured_hz = f_s;
            turnover->points[turnover->n_points].delta_f_ppm =
                (f_s - sweep->f_center_hz) / sweep->f_center_hz * 1e6f;
            turnover->n_points++;

            last_temp = current_temp;
        }
        HAL_Delay(100);
    }

    /* Phase 2: Cooling */
    heater_enable(false);
    while (heater_read_temp() > temp_start + 2.0f && turnover->n_points < TEMP_POINTS_MAX) {
        float current_temp = heater_read_temp();
        if (fabsf(current_temp - last_temp) >= temp_step) {
            sweep_single_point(sweep, sweep->f_center_hz, cal);

            float f_s = 0;
            float max_mag = 0;
            for (int i = 0; i < sweep->n_points; i++) {
                if (sweep->points[i].mag > max_mag) {
                    max_mag = sweep->points[i].mag;
                    f_s = sweep->points[i].freq_hz;
                }
            }

            turnover->points[turnover->n_points].temp_c = current_temp;
            turnover->points[turnover->n_points].f_measured_hz = f_s;
            turnover->points[turnover->n_points].delta_f_ppm =
                (f_s - sweep->f_center_hz) / sweep->f_center_hz * 1e6f;
            turnover->n_points++;

            last_temp = current_temp;
        }
        HAL_Delay(200);
    }

    return (turnover->n_points >= 5) ? 0 : -1;
}

int turnover_fit(turnover_t *turnover)
{
    /* Fit Δf/f₀(T) = a₀ + a₁(T-Tref) + a₂(T-Tref)² + a₃(T-Tref)³
     * using least-squares polynomial regression.
     * Tref is chosen as the minimum frequency point (turnover temperature). */

    if (turnover->n_points < 5) return -1;

    /* Find turnover temperature (minimum |Δf/f₀|) */
    float min_delta_f = 1e9f;
    int min_idx = 0;
    for (int i = 0; i < turnover->n_points; i++) {
        float abs_df = fabsf(turnover->points[i].delta_f_ppm);
        if (abs_df < min_delta_f) {
            min_delta_f = abs_df;
            min_idx = i;
        }
    }

    float Tref = turnover->points[min_idx].temp_c;
    turnover->T0 = Tref;

    /* Build normal equations for 3rd-order polynomial */
    float S[4][5] = {{0}};
    for (int i = 0; i < turnover->n_points; i++) {
        float x = turnover->points[i].temp_c - Tref;
        float y = turnover->points[i].delta_f_ppm;

        S[0][0] += 1;     S[0][1] += x;     S[0][2] += x*x;   S[0][3] += x*x*x;   S[0][4] += y;
        S[1][0] += x;     S[1][1] += x*x;   S[1][2] += x*x*x;  S[1][3] += x*x*x*x;  S[1][4] += x*y;
        S[2][0] += x*x;   S[2][1] += x*x*x; S[2][2] += x*x*x*x; S[2][3] += x*x*x*x*x; S[2][4] += x*x*y;
        S[3][0] += x*x*x; S[3][1] += x*x*x*x; S[3][2] += x*x*x*x*x; S[3][3] += x*x*x*x*x*x; S[3][4] += x*x*x*y;
    }

    /* Gaussian elimination */
    for (int col = 0; col < 4; col++) {
        /* Pivot */
        float max_val = fabsf(S[col][col]);
        int max_row = col;
        for (int row = col + 1; row < 4; row++) {
            if (fabsf(S[row][col]) > max_val) {
                max_val = fabsf(S[row][col]);
                max_row = row;
            }
        }
        if (max_row != col) {
            for (int j = 0; j < 5; j++) {
                float tmp = S[col][j]; S[col][j] = S[max_row][j]; S[max_row][j] = tmp;
            }
        }
        /* Eliminate */
        for (int row = col + 1; row < 4; row++) {
            float factor = S[row][col] / S[col][col];
            for (int j = col; j < 5; j++) {
                S[row][j] -= factor * S[col][j];
            }
        }
    }

    /* Back-substitution */
    float a[4];
    for (int i = 3; i >= 0; i--) {
        a[i] = S[i][4];
        for (int j = i + 1; j < 4; j++) {
            a[i] -= S[i][j] * a[j];
        }
        a[i] /= S[i][i];
    }

    turnover->a0 = a[0];
    turnover->a1 = a[1];
    turnover->a2 = a[2];
    turnover->a3 = a[3];
    turnover->Tc = a[2];  /* temperature coefficient ≈ a₂ */

    turnover->valid = true;
    return 0;
}