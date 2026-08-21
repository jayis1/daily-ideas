/**
 * compound_lib.h — Compound library and k-NN matching
 *
 * 60-entry on-device library of known (n_D, V_D, dn/dT) fingerprints.
 * k-NN (k=3) classification in (n_D, V_D) space identifies the
 * measured liquid and provides a confidence score.
 */

#ifndef COMPOUND_LIB_H
#define COMPOUND_LIB_H

#include "refract_calc.h"
#include <stdint.h>

#define LIB_SIZE  60
#define KNN_K     3
#define MAX_NAME_LEN  16

/* Compound categories */
typedef enum {
    CAT_REFERENCE = 0,
    CAT_SOLVENT,
    CAT_POLYOL,
    CAT_COOLANT,
    CAT_OIL,
    CAT_FOOD,
    CAT_SOLUTION,
    CAT_BEVERAGE,
    CAT_DAIRY,
    CAT_CLINICAL,
    CAT_AUTOMOTIVE,
    CAT_PHARMA,
    CAT_COUNT
} compound_category_t;

typedef struct {
    char     name[MAX_NAME_LEN];
    float    n_D;       /* RI at 589 nm, 20°C */
    float    abbe_vd;   /* Abbe number V_D */
    float    dn_dt;     /* Temperature coefficient (×10⁻⁴ /°C, negative) */
    uint8_t  category;
} compound_entry_t;

/* Match result */
typedef struct {
    int8_t   indices[KNN_K];  /* Library indices of k nearest */
    float    distances[KNN_K];
    float    confidence;      /* 0.0–1.0 */
} knn_result_t;

/**
 * Initialize the compound library (load from flash if available).
 */
void compound_lib_init(void);

/**
 * Match a measurement result against the library using k-NN.
 * Updates result->compound_id, result->compound_name, result->confidence.
 *
 * @param result  Measurement result (n_D and abbe_vd must be set)
 */
void compound_lib_match(ri_result_t *result);

/**
 * Get the full k-NN match details.
 */
void compound_lib_match_detail(ri_result_t *result, knn_result_t *knn);

/**
 * Get a library entry by index.
 */
const compound_entry_t *compound_lib_get(uint8_t index);

/**
 * Add or update a custom library entry.
 */
void compound_lib_set(uint8_t index, const compound_entry_t *entry);

/**
 * Get library size.
 */
uint8_t compound_lib_size(void);

#endif /* COMPOUND_LIB_H */