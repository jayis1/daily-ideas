/* identify.h — Compound identification from detected peaks
 *
 * Converts peak retention times to Kovats RI, matches against the
 * library, and estimates concentration from peak area.
 */
#ifndef IDENTIFY_H
#define IDENTIFY_H

#include "peak.h"
#include "library.h"

#define IDENTIFY_MAX_PEAKS   PEAK_MAX_PER_RUN
#define IDENTIFY_TOP_MATCHES 3

typedef struct {
    float    retention_s;
    float    retention_index;
    float    est_conc_ppm;
    library_match_t matches[IDENTIFY_TOP_MATCHES];
    int      n_matches;
    float    area_uv_s;
    float    height_uv;
} identification_t;

/* Identify all peaks in a chromatogram.
 *   peaks    — array from peak_detect()
 *   n_peaks  — number of peaks
 *   sample_vol_ml — sample volume (for concentration estimate)
 *   out      — output array
 * Returns number of identifications (== n_peaks). */
int identify_peaks(const peak_t *peaks, int n_peaks, float sample_vol_ml,
                   identification_t *out);

#endif /* IDENTIFY_H */