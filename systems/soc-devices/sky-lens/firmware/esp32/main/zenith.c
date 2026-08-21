/*
 * zenith.c — zenith histogram (5° bins) + cos²θ fit
 *
 * Accumulates per-event zenith angles into 18 bins (0..90°, 5° each).
 * Fits I(θ) = I(0)·cos²θ to the histogram and reports I(0) and χ².
 * The cos²θ law is the classic sea-level muon angular distribution.
 */
#include "zenith.h"
#include "sky_lens.h"
#include <string.h>
#include <math.h>

static uint32_t s_bins[ZENITH_BINS];

void zenith_init(void) { zenith_clear(); }
void zenith_clear(void) { memset(s_bins, 0, sizeof(s_bins)); }

void zenith_add(float zenith_deg)
{
    if (zenith_deg < 0.0f) zenith_deg = -zenith_deg;
    if (zenith_deg >= 90.0f) zenith_deg = 89.99f;
    int b = (int)(zenith_deg / 90.0f * (float)ZENITH_BINS);
    if (b < 0) b = 0; if (b >= ZENITH_BINS) b = ZENITH_BINS - 1;
    s_bins[b]++;
}

void zenith_get_bins(uint32_t *bins, int n)
{
    if (n > ZENITH_BINS) n = ZENITH_BINS;
    memcpy(bins, s_bins, n * sizeof(uint32_t));
}

/* Fit I(θ) = I0 · cos²θ to the histogram by least-squares.
 * We linearise: y = I/cos²θ should be ≈ I0, so we fit a constant to
 * the weighted data. χ² is computed against the cos²θ model.
 */
zenith_fit_t zenith_fit(void)
{
    zenith_fit_t result;
    memset(&result, 0, sizeof(result));

    /* Total counts (excluding any empty bins) */
    double sum_y = 0, sum_w = 0;
    double chi2 = 0;
    int n_used = 0;

    for (int i = 0; i < ZENITH_BINS; i++) {
        float th_center = (i + 0.5f) * (90.0f / ZENITH_BINS);    /* deg */
        float th_rad = th_center * (3.14159265f / 180.0f);
        float c2 = cosf(th_rad) * cosf(th_rad);
        if (c2 < 0.01f) continue;     /* skip near-horizon (low statistics) */
        float y = (float)s_bins[i];
        if (y < 1.0f) continue;       /* skip empty bins */
        /* Weighted: I0 = Σ(y / c2 * c2) / Σ(c2) = Σy / Σc2 — but use
         * the standard I0 = Σ(y) / Σ(c2) for the cos²θ model. */
        sum_y += y;
        sum_w += c2;
        n_used++;
    }

    if (sum_w > 0 && n_used > 1) {
        result.i0 = (float)(sum_y / sum_w);
        /* χ² against the model */
        for (int i = 0; i < ZENITH_BINS; i++) {
            float th_center = (i + 0.5f) * (90.0f / ZENITH_BINS);
            float th_rad = th_center * (3.14159265f / 180.0f);
            float c2 = cosf(th_rad) * cosf(th_rad);
            if (c2 < 0.01f) continue;
            float model = result.i0 * c2;
            float obs = (float)s_bins[i];
            if (model > 0)
                chi2 += (obs - model) * (obs - model) / model;
        }
        result.chi2 = (float)chi2 / (n_used > 2 ? (float)(n_used - 2) : 1.0f);
    } else {
        result.i0 = 0;
        result.chi2 = 0;
    }
    result.residual = 0;
    return result;
}