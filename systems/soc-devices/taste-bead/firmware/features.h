/* features.h — Feature extraction from EIS impedance spectra
 *
 * Extracts a compact 48-dimensional feature vector from the raw 5-electrode
 * × 20-frequency impedance matrix for use by the k-NN classifier.
 */

#ifndef TASTE_BEAD_FEATURES_H
#define TASTE_BEAD_FEATURES_H

#include "eis.h"
#include "bme280.h"
#include <stdint.h>

/* Per-electrode equivalent circuit parameters (Randles model) */
typedef struct {
    float R_s;          /* Solution resistance (Ω) */
    float R_ct;         /* Charge-transfer resistance (Ω) */
    float C_dl;         /* Double-layer capacitance (F) */
    float sigma_w;      /* Warburg diffusion coefficient (Ω·s^−0.5) */
    float peak_freq;    /* Characteristic peak frequency (Hz) */
    float z_at_100hz;   /* |Z| at 100 Hz (simple feature) */
    float z_ratio;      /* |Z(1Hz)| / |Z(100kHz)| (dispersion) */
} electrode_features_t;

/* Extract features from EIS result */
esp_err_t features_extract(const eis_result_t *eis,
                            float features[NUM_FEATURES],
                            const bme280_data_t *ambient);

/* Extract per-electrode Randles parameters from impedance spectrum */
void features_extract_electrode(const ad5941_z_point_t *spectrum,
                                  electrode_features_t *ef);

/* Normalize features to zero-mean, unit-variance using stored PCA loadings */
void features_pca_project(const float raw[NUM_FEATURES],
                           float projected[NUM_FEATURES]);

#endif /* TASTE_BEAD_FEATURES_H */