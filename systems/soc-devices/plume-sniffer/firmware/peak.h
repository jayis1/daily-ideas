/* peak.h — Chromatogram peak detection
 *
 * Operates on TCD samples (baseline-corrected µV). Detects peaks using a
 * derivative-threshold + second-derivative refinement approach.
 */
#ifndef PEAK_H
#define PEAK_H

#include "tcd.h"

#define PEAK_MAX_PER_RUN   64

typedef struct {
    float    retention_s;   /* apex time since run start, seconds */
    float    area_uv_s;     /* integrated peak area, µV·s */
    float    height_uv;     /* peak apex height above baseline, µV */
    float    width_s;       /* peak width at base, seconds */
    int      start_idx;     /* sample index at peak start */
    int      apex_idx;      /* sample index at apex */
    int      end_idx;       /* sample index at peak end */
} peak_t;

/* Detect peaks in a chromatogram buffer.
 *   samples   — array of TCD samples (baseline-corrected)
 *   n         — number of samples
 *   noise_sig — noise sigma (µV) from tcd_noise_sigma()
 *   peaks     — output array
 *   max_peaks — capacity of peaks array
 * Returns number of peaks found. */
int peak_detect(const tcd_sample_t *samples, int n, float noise_sig,
                peak_t *peaks, int max_peaks);

#endif /* PEAK_H */