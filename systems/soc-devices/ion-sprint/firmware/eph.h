/*
 * eph.h — Electropherogram processing: baseline correction, peak detection
 */

#ifndef EPH_H
#define EPH_H

#include <stdint.h>

typedef struct {
    float migration_time;   /* seconds from injection */
    float height;            /* peak height (arbitrary units) */
    float area;              /* peak area (trapezoidal integration) */
    float skewness;          /* peak shape skewness (for k-NN) */
    float start_time;        /* peak start (s) */
    float end_time;          /* peak end (s) */
} peak_t;

/* Initialize electropherogram processing module */
void eph_init(void);

/* Detect peaks in electropherogram using ALS baseline + derivative method.
 * Returns number of peaks found, fills peaks[] array. */
uint8_t eph_detect_peaks(const float *eph, uint32_t count,
                         peak_t *peaks, uint8_t max_peaks);

/* Asymmetric least squares baseline correction.
 * λ = smoothness, p = asymmetry (small p → asymmetric).
 * Returns baseline-corrected signal in-place. */
void eph_als_baseline(float *signal, uint32_t count, float lambda, float p);

#endif /* EPH_H */