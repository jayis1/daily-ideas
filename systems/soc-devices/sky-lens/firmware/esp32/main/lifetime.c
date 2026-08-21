/*
 * lifetime.c — muon-lifetime (prompt–delayed) mode + exponential fit
 *
 * In lifetime mode, the firmware looks for a prompt muon pulse followed
 * by a delayed decay-electron pulse on the same tile within a 20 µs
 * window. The inter-event delays are histogrammed (200 bins × 100 ns).
 * An exponential fit N(t) = N0·exp(-t/τ) + bg extracts τ_µ ≈ 2.197 µs.
 *
 * Fit method: linearise by taking log(N - bg). We first estimate bg as
 * the mean of the last 20 bins, then fit log(N-bg) vs t by least-squares.
 */
#include "lifetime.h"
#include "sky_lens.h"
#include <string.h>
#include <math.h>

static uint32_t s_delays[LIFETIME_BINS];    /* 100 ns bins, 0..20 µs */
static uint32_t s_n_pairs = 0;

void lifetime_init(void) { lifetime_clear(); }
void lifetime_clear(void)
{
    memset(s_delays, 0, sizeof(s_delays));
    s_n_pairs = 0;
}

void lifetime_add_delay(float dt_us)
{
    if (dt_us < 0 || dt_us >= 20.0f) return;
    int bin = (int)(dt_us / 20.0f * (float)LIFETIME_BINS);
    if (bin < 0) bin = 0; if (bin >= LIFETIME_BINS) bin = LIFETIME_BINS - 1;
    s_delays[bin]++;
    s_n_pairs++;
}

void lifetime_get_delays(uint32_t *out, int n)
{
    if (n > LIFETIME_BINS) n = LIFETIME_BINS;
    memcpy(out, s_delays, n * sizeof(uint32_t));
}

/* ── Exponential fit ────────────────────────────────────────────────────
 * Model: N(t) = N0 · exp(-t/τ) + bg
 * 1. Estimate bg as the mean of the tail (last 20 bins, t > 18 µs).
 * 2. For bins where N > bg + 1, compute y = ln(N - bg).
 * 3. Linear fit y = a + b·t  →  τ = -1/b,  N0 = exp(a).
 * 4. Compute χ² and the error on τ from the fit variance.
 */
lifetime_result_t lifetime_fit(void)
{
    lifetime_result_t r;
    memset(&r, 0, sizeof(r));
    r.n_pairs = s_n_pairs;
    if (s_n_pairs < 20) {
        r.tau_us = 0;
        return r;     /* not enough data */
    }

    /* 1. Background estimate from the tail (t > 15 µs, last 50 bins) */
    float bg_sum = 0;
    int bg_n = 0;
    for (int i = (int)(LIFETIME_BINS * 0.75f); i < LIFETIME_BINS; i++) {
        bg_sum += (float)s_delays[i];
        bg_n++;
    }
    r.bg_per_bin = bg_n > 0 ? bg_sum / (float)bg_n : 0;

    /* 2. Linear fit ln(N - bg) = a + b·t
     * Restrict to the first 8 µs (160 bins) where the signal dominates
     * and the log is well-defined. */
    double Sx = 0, Sy = 0, Sxx = 0, Sxy = 0;
    int n_fit = 0;
    float bin_us = 20.0f / (float)LIFETIME_BINS;   /* 0.1 µs */
    int fit_end = (int)(8.0f / bin_us);   /* 80 bins = 8 µs */
    for (int i = 0; i < fit_end; i++) {
        float n = (float)s_delays[i];
        float y = n - r.bg_per_bin;
        if (y < 1.0f) continue;     /* skip bins where log is unstable */
        float t = (i + 0.5f) * bin_us;
        float ly = logf(y);
        Sx  += t;  Sy  += ly;
        Sxx += t*t; Sxy += t*ly;
        n_fit++;
    }

    if (n_fit < 4) {
        r.tau_us = 0;
        return r;
    }

    /* Least-squares slope/intercept */
    double D = (double)n_fit * Sxx - Sx * Sx;
    if (fabs(D) < 1e-12) {
        r.tau_us = 0;
        return r;
    }
    double b = ((double)n_fit * Sxy - Sx * Sy) / D;     /* slope */
    double a = (Sy - b * Sx) / (double)n_fit;            /* intercept */

    if (fabs(b) < 1e-9) {
        r.tau_us = 0;
        return r;
    }
    r.tau_us = (float)(-1.0 / b);

    /* 3. χ² and error on τ (over the fit range) */
    double chi2 = 0;
    double var_b = 0;
    for (int i = 0; i < fit_end; i++) {
        float n = (float)s_delays[i];
        float y = n - r.bg_per_bin;
        if (y < 1.0f) continue;
        float t = (i + 0.5f) * bin_us;
        float model = expf((float)(a + b * t)) + r.bg_per_bin;
        if (model > 0)
            chi2 += (n - model) * (n - model) / model;
        float resid = logf(y) - (float)(a + b * t);
        var_b += resid * resid;
    }
    r.chi2 = (float)(chi2 / (n_fit > 2 ? (n_fit - 2) : 1));
    /* Error on τ: σ_τ = |1/b²| · σ_b, with σ_b ≈ sqrt(var_b / D) */
    double sigma_b = sqrt(var_b / D / (double)n_fit);
    r.tau_err_us = (float)fabs(1.0 / (b * b) * sigma_b);

    return r;
}