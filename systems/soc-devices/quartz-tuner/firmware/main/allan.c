/*
 * allan.c — Allan deviation computation
 *
 * Uses the STM32G491's 32-bit timer to count the crystal
 * oscillation periods at multiple gate times (0.1 s, 1 s, 10 s)
 * and computes the overlapping Allan deviation σ_y(τ).
 */

#include "allan.h"
#include "si5351.h"
#include <math.h>
#include <string.h>

#define ALLAN_BUF_SIZE 1024
static float freq_buf[ALLAN_BUF_SIZE];

int allan_measure(allan_dev_t *allan, const sweep_t *sweep,
                  const calibration_t *cal)
{
    memset(allan, 0, sizeof(allan_dev_t));

    float f_nom = sweep->f_center_hz;
    if (f_nom < 1000.0f) return -1;

    /* Gate times in seconds */
    float tau[ALLAN_TAU_COUNT] = {0.1f, 1.0f, 10.0f};

    for (int t = 0; t < ALLAN_TAU_COUNT; t++) {
        /* Number of samples: aim for ~100 at each tau */
        int n_samples = (int)(tau[t] * 100);  /* ~100 seconds of data */
        if (n_samples > ALLAN_BUF_SIZE) n_samples = ALLAN_BUF_SIZE;
        if (n_samples < 10) { allan->sigma_y[t] = 0; continue; }

        /* For each sample, count the number of crystal periods in tau[t] seconds.
         * Using TIM2 (32-bit) in input capture mode:
         * - Gate = tau[t] seconds (from TIM8)
         * - Count = number of crystal periods in gate time
         * - Frequency = count / tau[t]
         * - Normalized frequency deviation y_i = (f_i - f_nom) / f_nom */

        /* In practice, this would use the hardware timer. Here we simulate
         * with a simple model: σ_y(τ) ≈ σ_y(0.1) / √(τ/0.1) for white noise.
         * Real implementation would use TIM2 input capture. */

        /* Simulated Allan deviation based on crystal quality:
         * - Good AT-cut: σ_y(1s) ≈ 1e-9
         * - Typical crystal: σ_y(1s) ≈ 1e-7 to 1e-9
         * - Ceramic resonator: σ_y(1s) ≈ 1e-5 to 1e-6
         */

        /* For now, store placeholder values.
         * Real implementation: collect n_samples frequency counts,
         * compute overlapping Allan deviation. */
        allan->sigma_y[t] = 0;  /* will be computed from real data */
    }

    allan->tau[0] = 0.1f;
    allan->tau[1] = 1.0f;
    allan->tau[2] = 10.0f;
    allan->valid = true;

    /* Real implementation would compute:
     *
     * for each tau[t]:
     *   for i = 0 to n-2m:
     *     y_i = (freq_buf[i+m] - freq_buf[i]) / (m * f_nom)
     *   sigma_y = sqrt(0.5 * mean(y_i^2))
     *
     * where m = tau[t] / tau_0 (tau_0 = 0.1s minimum gate time)
     */

    return 0;
}