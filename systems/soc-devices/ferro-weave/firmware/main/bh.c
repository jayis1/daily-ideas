/*
 * bh.c — B-H loop computation (portable C, CORDIC-free fallback)
 *
 * Computes saturation flux density, coercivity, remanence, dc and
 * incremental permeability, specific core loss, and loop squareness from
 * sampled H (field, A/m) and B (flux, T) arrays covering one full
 * magnetizing cycle.
 *
 * The same source file compiles in both the STM32 firmware build and the
 * host simulation build. On the STM32 the inner loops could be offloaded
 * to the CORDIC/FMAC accelerators, but the pure-C path here is fast
 * enough at 4096 points (the bottleneck is the ADC DMA, not the math).
 */
#include "bh.h"
#include <math.h>
#include <string.h>

#define MU0 1.2566370614e-6f   /* permeability of vacuum, T·m/A */

/* ── Air-flux correction ──────────────────────────────────────────────── */
void bh_air_flux_correct(float *B, const float *H, int n, const geom_t *g)
{
    /* Air fraction inside the secondary winding. */
    float air_frac = 0.0f;
    if (g->a2 > 0.0f)
        air_frac = (g->a2 - g->a_core) / g->a2;
    float k = MU0 * air_frac;
    for (int i = 0; i < n; i++)
        B[i] -= k * H[i];
}

/* ── Loop area via shoelace ───────────────────────────────────────────── */
float bh_loop_area(const float *H, const float *B, int n)
{
    if (n < 3) return 0.0f;
    double area = 0.0;
    for (int i = 0; i < n; i++) {
        int j = (i + 1) % n;
        area += (double)H[i] * (double)B[j] - (double)H[j] * (double)B[i];
    }
    /* shoelace gives 2× signed area; take abs/2 */
    float a = (float)fabs(area) * 0.5f;
    return a;  /* T·A/m == J/m^3 (energy density per cycle) */
}

/* ── Coercivity Hc: H at the B=0 crossing ────────────────────────────── */
float bh_find_hc(const float *H, const float *B, int n)
{
    /* Find the zero crossing of B with the largest |H| (the coercive
     * point is the crossing on the loop's steep side). */
    float best_h = 0.0f;
    float best_abs_h = 0.0f;
    for (int i = 0; i < n; i++) {
        int j = (i + 1) % n;
        if ((B[i] <= 0.0f && B[j] > 0.0f) ||
            (B[i] > 0.0f  && B[j] <= 0.0f)) {
            /* linear interpolation to the zero crossing */
            float frac = -B[i] / (B[j] - B[i]);
            float h0 = H[i] + frac * (H[j] - H[i]);
            if (fabsf(h0) > best_abs_h) {
                best_abs_h = fabsf(h0);
                best_h = h0;
            }
        }
    }
    return best_h;
}

/* ── Remanence Br: B at the H=0 crossing ─────────────────────────────── */
float bh_find_br(const float *H, const float *B, int n)
{
    float best_b = 0.0f;
    float best_abs_b = 0.0f;
    for (int i = 0; i < n; i++) {
        int j = (i + 1) % n;
        if ((H[i] <= 0.0f && H[j] > 0.0f) ||
            (H[i] > 0.0f  && H[j] <= 0.0f)) {
            float frac = -H[i] / (H[j] - H[i]);
            float b0 = B[i] + frac * (B[j] - B[i]);
            if (fabsf(b0) > best_abs_b) {
                best_abs_b = fabsf(b0);
                best_b = b0;
            }
        }
    }
    return best_b;
}

/* ── Full computation ────────────────────────────────────────────────── */
int bh_compute(const float *H, const float *B_in, int n,
               const geom_t *g, bh_result_t *out)
{
    if (!H || !B_in || !out || n < 8) return -1;
    if (!g || g->n1 == 0 || g->n2 == 0) return -1;

    /* Work on a local copy so we can air-flux-correct in place. */
    float B[4096];
    if (n > 4096) n = 4096;
    memcpy(B, B_in, sizeof(float) * n);
    bh_air_flux_correct(B, H, n, g);

    /* B_sat = max |B| */
    float b_peak = 0.0f;
    for (int i = 0; i < n; i++)
        if (fabsf(B[i]) > b_peak) b_peak = fabsf(B[i]);

    /* H_peak for permeability */
    float h_peak = 0.0f;
    for (int i = 0; i < n; i++)
        if (fabsf(H[i]) > h_peak) h_peak = fabsf(H[i]);

    /* Hc and Br */
    float hc = bh_find_hc(H, B, n);
    float br = bh_find_br(H, B, n);

    /* Loop area → specific core loss P_v (W/kg)
     *   loop_area [T·A/m = J/m^3 per cycle]
     *   × freq [cycles/s]  → W/m^3
     *   / rho [kg/m^3]     → W/kg
     */
    float area = bh_loop_area(H, B, n);
    float p_v = (g->rho > 0.0f) ? (area * g->freq / g->rho) : 0.0f;

    /* DC relative permeability: slope origin→(H_peak,B_peak) / mu0
     *   mu_dc = (B_peak / H_peak) / mu0
     */
    float mu_dc = 0.0f;
    if (h_peak > 1e-3f)
        mu_dc = (b_peak / h_peak) / MU0;

    /* Peak incremental permeability: max local dB/dH / mu0.
     * Computed via central differences. */
    float mu_inc_peak = 0.0f;
    for (int i = 1; i < n - 1; i++) {
        float dh = H[i + 1] - H[i - 1];
        if (fabsf(dh) < 1e-6f) continue;
        float db = B[i + 1] - B[i - 1];
        float mu_inc = fabsf(db / dh) / MU0;
        if (mu_inc > mu_inc_peak) mu_inc_peak = mu_inc;
    }

    /* Squareness */
    float sq = (b_peak > 1e-6f) ? (fabsf(br) / b_peak) : 0.0f;

    out->b_sat        = b_peak;
    out->h_c          = hc;
    out->b_r          = br;
    out->mu_dc        = mu_dc;
    out->mu_inc_peak  = mu_inc_peak;
    out->p_v          = p_v;
    out->squareness   = sq;
    out->loop_area    = area;
    out->n_points     = n;
    return 0;
}