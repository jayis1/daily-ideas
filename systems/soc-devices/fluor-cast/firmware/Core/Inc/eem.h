/*
 * eem.h — Excitation-Emission Matrix acquisition and processing
 */

#ifndef EEM_H
#define EEM_H

#include <stdint.h>
#include "config.h"
#include "fluorometer.h"

/* EEM matrix: 8 excitation × 256 emission pixels */
typedef struct {
    fluor_result_t spectra[EEM_ROWS];  /* per-excitation results */
    uint16_t matrix[EEM_ROWS][CCD_PIXELS]; /* normalized EEM data */
    uint16_t matrix_mask[EEM_ROWS][CCD_PIXELS]; /* scatter mask (1=valid, 0=masked) */
    float features[FEATURE_COUNT];   /* extracted features */
    float temp_c;                     /* sample temperature */
    uint32_t timestamp;               /* RTC timestamp */
    uint32_t duration_ms;             /* total acquisition time */
    uint8_t  valid;                   /* EEM valid flag */
} eem_t;

/**
 * Initialize EEM subsystem.
 */
void eem_init(void);

/**
 * Acquire a full EEM: sweep all 8 excitation wavelengths, capture emission.
 * @param params  Acquisition parameters
 * @param eem     Output EEM structure
 * @return 0 on success, -1 on error
 */
int eem_acquire(const acq_params_t *params, eem_t *eem);

/**
 * Process raw EEM: apply scatter masking, normalization, feature extraction.
 * @param eem  EEM structure (modified in-place)
 */
void eem_process(eem_t *eem);

/**
 * Mask Rayleigh scatter regions (1st and 2nd order) around each excitation.
 * Marks ±15 nm window around λ_ex and λ_ex/2 in the emission axis.
 */
void eem_mask_scatter(eem_t *eem);

/**
 * Mask water Raman scatter peak.
 * Raman shift ≈ 3400 cm⁻¹ → λ_raman = 1/(1/λ_ex - 3400e-7)
 */
void eem_mask_raman(eem_t *eem);

/**
 * Apply inner filter effect (IFE) correction if absorbance data available.
 * @param eem  EEM structure
 * @param a_ex Array of absorbance values at each excitation wavelength
 * @param a_em Array of absorbance values at each emission wavelength
 */
void eem_apply_ife(eem_t *eem, const float *a_ex, const float *a_em);

/**
 * Extract 48 features from EEM for classification.
 * Features: band integrals, peak info, fluorescence indices, PCA scores.
 */
void eem_extract_features(eem_t *eem);

/**
 * Compute fluorescence indices:
 * - FI (fluorescence index): 450/500 nm @ 370 nm ex
 * - BIX (biological index): 380/430 nm @ 310 nm ex
 * - HIX (humification index): 435-480/300-345 @ 254 nm ex
 * - β/α (freshness index): 380/460-480 @ 310 nm ex
 */
void eem_compute_indices(const eem_t *eem, float *fi, float *bix, float *hix, float *beta_alpha);

/**
 * Get EEM data at specific excitation/emission indices.
 */
uint16_t eem_get(const eem_t *eem, uint8_t ex_idx, uint16_t pixel);

/**
 * Get EEM data at specific excitation (nm) / emission (nm).
 * Returns 0 if outside range or masked.
 */
uint16_t eem_get_nm(const eem_t *eem, float ex_nm, float em_nm);

/**
 * Compute EEM volume (total fluorescence integral).
 */
float eem_volume(const eem_t *eem);

/**
 * Compute EEM centroid (weighted mean ex/em wavelength).
 */
void eem_centroid(const eem_t *eem, float *ex_mean_nm, float *em_mean_nm);

#endif /* EEM_H */