/*
 * library.h — 50-compound fluorescence library and k-NN classifier
 */

#ifndef LIBRARY_H
#define LIBRARY_H

#include <stdint.h>
#include "config.h"
#include "eem.h"

/* Compound entry in the fluorescence library */
typedef struct {
    char     name[32];        /* compound name */
    char     category[16];    /* category string */
    uint16_t ex_peak_nm;      /* primary excitation peak (nm) */
    uint16_t em_peak_nm;      /* primary emission peak (nm) */
    float    features[FEATURE_COUNT]; /* 48-dim feature vector */
    float    calib_a;          /* calibration: conc = a × intensity + b */
    float    calib_b;
    float    calib_r2;        /* calibration R² */
} library_entry_t;

/* Classification result */
typedef struct {
    uint8_t  indices[KNN_K];    /* top-k library indices */
    float    distances[KNN_K];  /* Euclidean distances */
    float    confidences[KNN_K]; /* confidence scores (0–1) */
    uint8_t  top_match;        /* best match index */
    float    top_confidence;   /* best match confidence */
    float    estimated_conc;   /* estimated concentration (if applicable) */
} classify_result_t;

/**
 * Initialize library (load from flash or use defaults).
 */
void library_init(void);

/**
 * Get number of entries in library.
 */
uint8_t library_size(void);

/**
 * Get library entry by index.
 */
const library_entry_t *library_get(uint8_t index);

/**
 * Find compound by name (case-insensitive).
 * @return index or -1 if not found
 */
int library_find(const char *name);

/**
 * Classify an EEM using k-NN (k=5).
 * @param eem  Processed EEM with extracted features
 * @param result Output classification result
 * @return 0 on success, -1 on error
 */
int library_classify(const eem_t *eem, classify_result_t *result);

/**
 * Estimate concentration from fluorescence intensity.
 * Uses calibration curve of the matched compound.
 * @param entry Library entry for the compound
 * @param intensity Normalized peak intensity
 * @return Estimated concentration in µg/L
 */
float library_estimate_concentration(const library_entry_t *entry, float intensity);

/**
 * Apply Stern-Volmer quenching correction.
 * @param F0  Unquenched fluorescence
 * @param Ksv Stern-Volmer quenching constant (M⁻¹)
 * @param Q   Quencher concentration (M)
 * @return Corrected (unquenched) fluorescence
 */
float library_stern_volmer_correct(float F0, float Ksv, float Q);

/**
 * Update library entry (for calibration / new compounds).
 */
int library_update(uint8_t index, const library_entry_t *entry);

/**
 * Save library to flash.
 */
int library_save(void);

#endif /* LIBRARY_H */