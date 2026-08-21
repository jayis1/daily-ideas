/* library.h — Kovats retention-index compound library
 *
 * 40 compounds with their retention indices (RI) on a 5% OV-101
 * (non-polar, dimethylsilicone) column. RI values are approximate
 * for the default method (35→180°C @ 10°C/min, air carrier).
 * The library is embedded in flash and extensible via NVS.
 */
#ifndef LIBRARY_H
#define LIBRARY_H

#include <stdint.h>
#include <stdbool.h>

#define LIBRARY_MAX_ENTRIES    PLUME_LIBRARY_MAX_ENTRIES
#define LIBRARY_MAX_NAME_LEN   PLUME_LIBRARY_MAX_NAME_LEN

typedef struct {
    char     name[LIBRARY_MAX_NAME_LEN];
    uint16_t retention_index;   /* Kovats RI (n-alkane scale) */
    uint16_t cas_number;        /* CAS stored as compact uint (first 5 digits) */
    float    response_factor;   /* relative TCD response (propane=1.0) */
} library_entry_t;

/* Get the full library (pointer to static array). */
const library_entry_t *library_get_all(int *count);

/* Look up a single entry by index. */
const library_entry_t *library_get(int index);

/* Find top-3 matches by retention index proximity.
 *   ri       — measured retention index
 *   out      — output array of 3 (index, delta_ri) pairs
 *   max_conc — if non-NULL, filled with a rough concentration estimate (ppm)
 *              based on peak area and the response factor. */
typedef struct {
    int   index;       /* library index, -1 if none */
    float delta_ri;    /* |RI_measured - RI_library| */
} library_match_t;

int library_match(float ri, library_match_t *out, int max_out);

/* Compute Kovats RI from a measured retention time using stored n-alkane
 * calibration anchors (C5–C16). Returns -1 if out of range. */
float library_ri_from_rt(float retention_s);

/* Set / update the n-alkane calibration anchors (retention times for
 * n-C5 through n-C16). Stored in NVS. */
bool library_set_anchors(const float *rt_alkanes, int n);

/* Get the current anchors. */
int library_get_anchors(float *rt_alkanes, int max_n);

#endif /* LIBRARY_H */