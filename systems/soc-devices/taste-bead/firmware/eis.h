/* eis.h — Multi-electrode EIS measurement orchestration
 *
 * Coordinates the AD5941 AFE and electrode mux to perform a full
 * impedance spectroscopy sweep across all 5 electrodes at 20 frequencies.
 */

#ifndef TASTE_BEAD_EIS_H
#define TASTE_BEAD_EIS_H

#include "esp_err.h"
#include "ad5941.h"
#include <math.h>

/* Full EIS measurement result: 5 electrodes × 20 frequencies */
typedef struct {
    ad5941_z_point_t spectra[NUM_ELECTRODES][NUM_FREQS];
    float freqs[NUM_FREQS];
    float exc_amplitude;
    uint32_t rtia[NUM_ELECTRODES];
    int64_t timestamp_us;
    float liquid_temp_c;     /* Estimated from ambient + impedance shift */
} eis_result_t;

/* Initialize EIS engine */
esp_err_t eis_init(void);

/* Run full EIS sweep (all electrodes, all frequencies) */
esp_err_t eis_sweep(eis_result_t *result);

/* Run sweep for a single electrode (for calibration) */
esp_err_t eis_sweep_electrode(int electrode, ad5941_z_point_t *results);

/* Get frequency table */
const float *eis_get_freq_table(void);

/* Estimate liquid temperature from impedance shift
 * (speed of ion diffusion changes with temperature, shifting low-freq Z) */
float eis_estimate_temperature(const eis_result_t *result,
                                 float ambient_temp_c);

#endif /* TASTE_BEAD_EIS_H */