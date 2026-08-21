/*
 * dent-scope / Core/Src/indentation.c
 * Dent Scope — Oliver–Pharr instrumented indentation analysis
 *
 * Implements the Oliver–Pharr method (J. Mater. Res. 1992, 2004) for
 * extracting hardness and elastic modulus from load–displacement curves.
 *
 * Key equations:
 *   S = dP/dh at h_max  (unloading slope, upper 30-60% fit)
 *   h_c = h_max − ε·P_max / S    (ε = 0.75 for Vickers/Berkovich)
 *   A = 24.5·h_c²                (Vickers/Berkovich projected area)
 *   H = P_max / A                (hardness)
 *   E_r = S / (2·β·√(A/π))       (reduced modulus, β=1.012 Vickers)
 *   E = (1−ν²) / (1/E_r − (1−ν_i²)/E_i)   (Young's modulus)
 *     E_i = 1141 GPa, ν_i = 0.07 (diamond)
 *
 * Also computes:
 *   W_total  = ∫₀^h_max P dh    (area under loading curve)
 *   W_elastic = ∫_{h_f}^h_max P dh (area under unloading curve)
 *   η = W_elastic / W_total      (elastic work ratio)
 *
 * MIT License.
 */
#include "indentation.h"

static indent_result_t result;

/* Diamond indenter properties */
#define E_DIAMOND_GPa  1141.0f
#define NU_DIAMOND     0.07f

void indent_result_init(void)
{
    memset(&result, 0, sizeof(result));
}

void indentation_init(void)
{
    indent_result_init();
}

void indentation_reset(void)
{
    indent_result_init();
}

void indentation_push(float force_mN, float depth_um)
{
    if (result.count < INDENT_MAX_POINTS) {
        result.force_mN[result.count] = force_mN;
        result.depth_um[result.count]  = depth_um;
        result.count++;
    }
}

/* ---- Power-law unloading fit: P = α(h − h_f)^m ----
 * We fit the upper portion (30%-98% of peak force) of the unloading curve.
 * Levenberg–Marquardt iteration (simplified, 10 iterations).
 */
static void fit_unloading(int unload_start_idx, int unload_end_idx,
                          float *alpha, float *m, float *h_f)
{
    int n = unload_end_idx - unload_start_idx;
    if (n < 5) { *alpha = 0; *m = 1.5; *h_f = 0; return; }

    /* Use upper 30%-98% of unloading for fit */
    int lo = unload_start_idx + (int)(n * 0.02f);
    int hi = unload_start_idx + (int)(n * 0.70f);
    if (hi <= lo) { lo = unload_start_idx; hi = unload_end_idx - 1; }

    /* initial guesses */
    float hf = result.depth_um[unload_start_idx] * 0.3f; /* residual depth guess */
    float alpha_g = result.force_mN[unload_start_idx] /
                    powf(result.depth_um[unload_start_idx] - hf + 0.001f, 1.5f);
    float mg = 1.5f;

    /* Levenberg–Marquardt (simplified) */
    float lambda = 0.01f;
    for (int iter = 0; iter < 10; iter++) {
        float J11 = 0, J12 = 0, J21 = 0, J22 = 0;
        float r1 = 0, r2 = 0;
        for (int i = lo; i < hi; i++) {
            float h = result.depth_um[i] - hf;
            if (h < 0.001f) h = 0.001f;
            float hm = powf(h, mg);
            float Ppred = alpha_g * hm;
            float resid = result.force_mN[i] - Ppred;
            /* partial derivatives */
            float dPda = hm;
            float dPdm = alpha_g * hm * logf(h);
            J11 += dPda * dPda; J12 += dPda * dPdm;
            J21 += dPdm * dPda; J22 += dPdm * dPdm;
            r1 += dPda * resid;
            r2 += dPdm * resid;
        }
        /* regularize */
        J11 += lambda; J22 += lambda;
        /* solve 2×2: [J11 J12; J21 J22] [da; dm] = [r1; r2] */
        float det = J11 * J22 - J12 * J21;
        if (fabsf(det) < 1e-12f) break;
        float da = (J22 * r1 - J12 * r2) / det;
        float dm = (J11 * r2 - J21 * r1) / det;
        alpha_g += da;
        mg += dm;
        if (mg < 1.0f) mg = 1.0f;
        if (mg > 3.0f) mg = 3.0f;
        lambda *= 0.8f;
    }
    *alpha = alpha_g;
    *m = mg;
    *h_f = hf;
}

/* ---- Trapezoidal integration ---- */
static float trapz(float *x, float *y, int lo, int hi)
{
    float area = 0;
    for (int i = lo; i < hi; i++)
        area += 0.5f * (x[i+1] - x[i]) * (y[i] + y[i+1]);
    return area;
}

void indentation_finalize(void)
{
    /* Determine loading/unloading boundaries:
     * loading: from contact (first non-zero force) to peak
     * hold: plateau at peak (skip)
     * unloading: from peak down to near-zero force
     */
    if (result.count < 10) return;

    /* Find peak index (max force) */
    int peak_idx = 0;
    float peak_force = 0;
    for (int i = 0; i < result.count; i++) {
        if (result.force_mN[i] > peak_force) {
            peak_force = result.force_mN[i];
            peak_idx = i;
        }
    }

    /* Find unloading start: after peak, find where force starts decreasing */
    int unload_start = peak_idx;
    for (int i = peak_idx + 1; i < result.count; i++) {
        if (result.force_mN[i] < peak_force * 0.98f) {
            unload_start = i;
            break;
        }
    }

    /* Find unload end: force drops below 5% of peak */
    int unload_end = result.count - 1;
    for (int i = unload_start; i < result.count; i++) {
        if (result.force_mN[i] < peak_force * 0.05f) {
            unload_end = i;
            break;
        }
    }

    /* Fit unloading curve */
    float alpha, m, h_f;
    fit_unloading(unload_start, unload_end, &alpha, &m, &h_f);

    /* Contact stiffness S = dP/dh at h_max
     * For P = α(h−h_f)^m: dP/dh = α·m·(h_max−h_f)^(m−1) */
    float h_max = result.depth_um[peak_idx];
    float P_max = result.force_mN[peak_idx];
    float dh = h_max - h_f;
    if (dh < 0.001f) dh = 0.001f;
    result.S_mN_um = alpha * m * powf(dh, m - 1.0f);
    result.h_contact_um = h_max - 0.75f * P_max / result.S_mN_um; /* ε=0.75 */

    /* Contact area (Vickers/Berkovich: A = 24.5·h_c² in µm²) */
    float hc = result.h_contact_um;
    if (hc < 0) hc = 0;
    if (g_cfg.tip == TIP_WC_BALL_1MM) {
        /* Brinell: A = π·D·h_c, D = 1000 µm (1mm ball) */
        result.area_um2 = 3.14159f * 1000.0f * hc;
    } else {
        /* Vickers or Berkovich: A = 24.5·h_c² */
        result.area_um2 = 24.5f * hc * hc;
    }

    /* Hardness: H = P_max / A (P in mN, A in µm² → H in MPa = mN/µm² × 1000) */
    if (result.area_um2 > 0.001f)
        result.hardness_MPa = P_max / result.area_um2 * 1000.0f; /* MPa */
    else
        result.hardness_MPa = 0;

    /* Reduced modulus: E_r = S / (2·β·√(A/π))
     * S in mN/µm, A in µm² → E_r in MPa = mN/µm² × 1000 → GPa = /1000
     * β = 1.012 for Vickers, 1.034 for Berkovich */
    float beta = (g_cfg.tip == TIP_BERKOVICH) ? 1.034f : 1.012f;
    if (result.area_um2 > 0.001f) {
        float Er_MPa = result.S_mN_um / (2.0f * beta * sqrtf(result.area_um2 / 3.14159f));
        Er_MPa *= 1000.0f; /* mN/µm² → MPa */
        result.E_r_GPa = Er_MPa / 1000.0f; /* MPa → GPa */

        /* Young's modulus: 1/E = (1−ν²)/E_r − (1−ν_i²)/E_i */
        float nu = g_cfg.poisson;
        float inv_E = (1.0f - nu*nu) / (Er_MPa) - (1.0f - NU_DIAMOND*NU_DIAMOND) / (E_DIAMOND_GPa * 1000.0f);
        if (inv_E > 0)
            result.E_GPa = (1.0f / inv_E) / 1000.0f; /* MPa → GPa */
        else
            result.E_GPa = 0;
    } else {
        result.E_r_GPa = 0;
        result.E_GPa = 0;
    }

    /* Work: trapezoidal integration of P vs h */
    /* W_total: from first contact to peak (loading curve) */
    int contact_idx = 0;
    for (int i = 0; i < peak_idx; i++) {
        if (result.force_mN[i] > 1.0f) { contact_idx = i; break; }
    }
    result.W_total_nJ = trapz(result.depth_um, result.force_mN, contact_idx, peak_idx);
    /* W_elastic: from peak to unload end (unloading curve) */
    result.W_elastic_nJ = trapz(result.depth_um, result.force_mN, peak_idx, unload_end);
    if (result.W_total_nJ > 0.001f)
        result.eta = result.W_elastic_nJ / result.W_total_nJ;
    else
        result.eta = 0;
}

void indentation_compute(ds_status_t *st)
{
    st->peak_force_mN = result.force_mN[0];
    st->peak_depth_um = result.depth_um[0];
    /* find actual peak */
    for (int i = 0; i < result.count; i++) {
        if (result.force_mN[i] > st->peak_force_mN) {
            st->peak_force_mN = result.force_mN[i];
            st->peak_depth_um = result.depth_um[i];
        }
    }

    st->hardness_HV = result.hardness_MPa / 9.807f; /* MPa → kgf/mm² (HV) */
    st->hardness_HB = result.hardness_MPa / 9.807f; /* Brinell approx */
    st->modulus_E_GPa = result.E_GPa;
    st->elastic_ratio = result.eta;

    /* creep: depth change during hold / hold time
     * (computed from consecutive points at near-peak force) */
    /* simplified: use difference between peak and final hold point */
    st->creep_nm_s = 0; /* filled during hold in main loop if needed */
}

indent_result_t *indentation_get(void) { return &result; }