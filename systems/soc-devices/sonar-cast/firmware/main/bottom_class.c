/*
 * sonar-cast / firmware / bottom_class.c
 * Bottom-type classifier: hard / soft / weedy from echo-envelope statistics.
 *
 * Features:
 *   - rise_time:  10→90 % rise time of the bottom echo (samples)
 *   - decay_tail: e-folding decay time after the bottom peak
 *   - second_bounce_ratio: env@2×depth / env@depth
 *   - multi_peak: number of local maxima in the bottom echo window
 *
 * Classification: nearest-centroid (3 centroids, calibrated on known bottoms).
 */
#include "main.h"
#include <math.h>

const char *const BOTTOM_NAMES[4] = { "hard", "soft", "weedy", "unknown" };

/* Calibrated centroids (rise, decay, sb_ratio, multi_peak) for 200 kHz. */
static const float CENTROIDS[3][4] = {
    /* hard  */ { 2.0f, 18.0f, 0.35f, 1.0f },
    /* soft  */ { 6.0f,  6.0f, 0.10f, 1.0f },
    /* weedy */ { 4.0f, 30.0f, 0.05f, 4.0f },
};

static void extract_features(const float *env, uint32_t n, uint32_t bidx,
                             float *feat)
{
    if (bidx >= n || bidx < 4) {
        feat[0] = feat[1] = feat[2] = feat[3] = 0;
        return;
    }
    float peak = env[bidx];
    if (peak < 1e-6f) peak = 1e-6f;

    /* rise time 10→90 % */
    float v10 = peak * 0.10f, v90 = peak * 0.90f;
    int i10 = -1, i90 = -1;
    for (int j = (int)bidx; j >= 0 && j >= (int)bidx - 32; j--) {
        if (env[j] <= v10) { i10 = j; break; }
    }
    for (int j = (int)bidx; j < (int)n && j <= (int)bidx + 32; j++) {
        if (env[j] >= v90) { i90 = j; break; }
    }
    feat[0] = (i90 > 0 && i10 >= 0) ? (float)(i90 - i10) : 32.0f;

    /* decay tail: samples to fall to 1/e of peak */
    float inv_e = peak * 0.3679f;
    int dec = 0;
    for (int j = (int)bidx + 1; j < (int)n && j <= (int)bidx + 64; j++) {
        if (env[j] <= inv_e) break;
        dec++;
    }
    feat[1] = (float)dec;

    /* second-bounce ratio */
    uint32_t sb = bidx * 2;
    if (sb + 4 < n) {
        float sbpk = 0;
        for (uint32_t j = sb - 2; j <= sb + 2; j++) sbpk = (env[j] > sbpk) ? env[j] : sbpk;
        feat[2] = sbpk / peak;
    } else feat[2] = 0.0f;

    /* multi-peak count in [bidx-8, bidx+24] */
    int mp = 0;
    for (int j = (int)bidx - 8; j <= (int)bidx + 24; j++) {
        if (j < 2 || j >= (int)n - 1) continue;
        if (env[j] > peak * 0.4f && env[j] >= env[j-1] && env[j] >= env[j+1])
            mp++;
    }
    feat[3] = (float)mp;
}

void bottom_class_run(const float *env, uint32_t n, uint32_t bidx,
                      sonar_result_t *r)
{
    float feat[4];
    extract_features(env, n, bidx, feat);

    /* Nearest-centroid (Euclidean, normalized) */
    float best_d = 1e9f;
    uint8_t best = BT_UNKNOWN;
    for (int c = 0; c < 3; c++) {
        float d = 0;
        for (int f = 0; f < 4; f++) {
            float diff = (feat[f] - CENTROIDS[c][f]) / CENTROIDS[c][f];
            d += diff * diff;
        }
        if (d < best_d) { best_d = d; best = (uint8_t)c; }
    }
    r->bottom_type  = best;
    /* confidence: inverse distance, normalized */
    r->bottom_conf  = 1.0f / (1.0f + best_d);
}