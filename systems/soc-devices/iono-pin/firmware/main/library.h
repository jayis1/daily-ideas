/*
 * library.h — 45-compound reduced-mobility (K0) library + k-NN classifier
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * K0 values in cm^2/(V·s), positive-ion mode, air drift gas.
 * Values are representative literature/typical values for field-portable IMS.
 */
#ifndef LIBRARY_H
#define LIBRARY_H

#include "ims.h"
#include <stdint.h>

#define LIB_SIZE        45
#define LIB_KNN_K       5
#define LIB_FEATURE_DIM 1     /* K0-based (monomer/dimer pairs handled per-peak) */

typedef enum {
    CLASS_NONE = 0,
    CLASS_EXPLOSIVE,
    CLASS_DRUG,
    CLASS_CWA,
    CLASS_TIC,
    CLASS_VOC,
    CLASS_REFERENCE
} compound_class_t;

typedef struct {
    const char *name;
    float k0;                   /* reduced mobility cm^2/(V.s) */
    compound_class_t cls;
} lib_entry_t;

extern const lib_entry_t g_library[LIB_SIZE];
extern const uint8_t g_library_size;

typedef struct {
    const char *name;
    compound_class_t cls;
    float k0;
    float distance;             /* k-NN distance to matched peak */
    float confidence;           /* 0..1 (1 - dist/maxdist, averaged over k) */
} classify_result_t;

/* k-NN classify over the peak list */
void library_classify(const ims_peak_t *peaks, uint8_t n, classify_result_t *out);

#endif /* LIBRARY_H */