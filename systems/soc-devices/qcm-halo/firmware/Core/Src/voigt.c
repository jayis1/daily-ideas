/*
 * voigt.c — Voigt viscoelastic model fitting via Levenberg-Marquardt
 *
 * Implements the Voinova et al. (1999) model for a single Voigt
 * viscoelastic layer on a quartz crystal, loaded by a semi-infinite
 * Newtonian liquid.
 *
 * The model predicts Δf and ΔD at each overtone n as functions of:
 *   d_f  — film thickness (m)
 *   η_f  — film viscosity (Pa·s)
 *   μ_f  — film shear modulus (Pa)
 *   ρ_f  — film density (kg/m³)
 *
 * We fit d_f, η_f, μ_f (ρ_f is usually assumed or known).
 *
 * The QCM-D equation for a Voigt layer + liquid load:
 *
 *   Δf/n = -(1 / (2π * ρq * tq)) * Im(ξ)
 *   ΔD/n = (1 / (π * f0 * ρq * tq)) * (-Re(ξ))
 *
 * where ξ is the complex load impedance, and tq = thickness of quartz.
 *
 * For a Voigt layer on liquid:
 *   ξ = ξ_liquid * (ξ_film * cosh(kf * df) + ξ_liquid * sinh(kf * df)) /
 *       (ξ_liquid * cosh(kf * df) + ξ_film * sinh(kf * df))
 *
 * where:
 *   ξ_liquid = sqrt(ρ_l * (η_l * 2πi*f) )    — complex shear wave impedance of liquid
 *   ξ_film   = sqrt(ρ_f * (μ_f + η_l*2πi*f))  — complex shear wave impedance of film
 *   kf = sqrt(ρ_f * 2πi*f / (μ_f + η_f*2πi*f)) — complex wave number in film
 *   tq = sqrt(μq / ρq) / (2π * f0)             — quartz thickness
 */

#include "main.h"
#include <math.h>
#include <string.h>
#include "voigt.h"
#include "sauerbrey.h"

/* Complex number helpers */
typedef struct { float re, im; } cpx_t;

static inline cpx_t cpx_make(float re, float im) { cpx_t c = {re, im}; return c; }
static inline cpx_t cpx_add(cpx_t a, cpx_t b) { return cpx_make(a.re+b.re, a.im+b.im); }
static inline cpx_t cpx_sub(cpx_t a, cpx_t b) { return cpx_make(a.re-b.re, a.im-b.im); }
static inline cpx_t cpx_mul(cpx_t a, cpx_t b) {
    return cpx_make(a.re*b.re - a.im*b.im, a.re*b.im + a.im*b.re);
}
static inline cpx_t cpx_div(cpx_t a, cpx_t b) {
    float d = b.re*b.re + b.im*b.im;
    if (d < 1e-30f) d = 1e-30f;
    return cpx_make((a.re*b.re + a.im*b.im)/d, (a.im*b.re - a.re*b.im)/d);
}
static inline cpx_t cpx_scale(cpx_t a, float s) { return cpx_make(a.re*s, a.im*s); }
static inline float cpx_abs(cpx_t a) { return sqrtf(a.re*a.re + a.im*a.im); }

/* Complex square root: sqrt(a + bi) */
static cpx_t cpx_sqrt(cpx_t z)
{
    float r = cpx_abs(z);
    float re = sqrtf(fmaxf(0.0f, (r + z.re) / 2.0f));
    float im = (z.im >= 0 ? 1.0f : -1.0f) * sqrtf(fmaxf(0.0f, (r - z.re) / 2.0f));
    return cpx_make(re, im);
}

static inline cpx_t cpx_cosh(cpx_t z)
{
    /* cosh(a+bi) = cosh(a)cos(b) + i*sinh(a)sin(b) */
    return cpx_make(coshf(z.re)*cosf(z.im), sinhf(z.re)*sinf(z.im));
}

static inline cpx_t cpx_sinh(cpx_t z)
{
    /* sinh(a+bi) = sinh(a)cos(b) + i*cosh(a)sin(b) */
    return cpx_make(sinhf(z.re)*cosf(z.im), coshf(z.re)*sinf(z.im));
}

/* Compute the complex load impedance for a Voigt layer on liquid.
 *
 * f = overtone frequency (Hz)
 * df = film thickness (m)
 * eta_f = film viscosity (Pa·s)
 * mu_f = film shear modulus (Pa)
 * rho_f = film density (kg/m³)
 * rho_l = liquid density (kg/m³)
 * eta_l = liquid viscosity (Pa·s)
 *
 * Returns complex ξ such that:
 *   Δf/n = -Im(ξ) / (2π * ρq * tq)
 *   ΔD/n = -Re(ξ) / (π * f0 * ρq * tq)
 */
static cpx_t voigt_load_impedance(float f, float df, float eta_f, float mu_f,
                                   float rho_f, float rho_l, float eta_l)
{
    float omega = 2.0f * PI * f;
    cpx_t i_omega = cpx_make(0.0f, omega);

    /* Complex shear modulus of film: G_f = mu_f + i*omega*eta_f */
    cpx_t G_f = cpx_add(cpx_make(mu_f, 0.0f), cpx_scale(i_omega, eta_f));

    /* Complex shear modulus of liquid: G_l = i*omega*eta_l */
    cpx_t G_l = cpx_scale(i_omega, eta_l);

    /* Complex wave impedance:
     *   ξ_film = sqrt(ρ_f * G_f)
     *   ξ_liq  = sqrt(ρ_l * G_l)
     */
    cpx_t xi_f = cpx_sqrt(cpx_scale(G_f, rho_f));
    cpx_t xi_l = cpx_sqrt(cpx_scale(G_l, rho_l));

    /* Complex wave number in film: k_f = sqrt(ρ_f * ω² / G_f) */
    /* Actually k_f = sqrt(ρ_f * i*omega / G_f) */
    cpx_t kf = cpx_sqrt(cpx_div(cpx_scale(i_omega, rho_f), G_f));

    /* k_f * d_f */
    cpx_t kf_df = cpx_scale(kf, df);

    cpx_t cosh_kd = cpx_cosh(kf_df);
    cpx_t sinh_kd = cpx_sinh(kf_df);

    /* ξ = ξ_l * (ξ_f * cosh(kf*df) + ξ_l * sinh(kf*df)) /
     *        (ξ_l * cosh(kf*df) + ξ_f * sinh(kf*df))
     */
    cpx_t num = cpx_add(cpx_mul(xi_f, cosh_kd), cpx_mul(xi_l, sinh_kd));
    cpx_t den = cpx_add(cpx_mul(xi_l, cosh_kd), cpx_mul(xi_f, sinh_kd));

    return cpx_mul(xi_l, cpx_div(num, den));
}

/* Predict Δf and ΔD for given Voigt parameters at overtone frequency f.
 * f0 = fundamental frequency, n = overtone number
 */
void voigt_predict(const voigt_params_t *p, float f_n, float f0,
                   float rho_q, float mu_q,
                   float rho_l, float eta_l,
                   float *df_pred, float *dd_pred)
{
    float tq = sqrtf(mu_q / rho_q) / (2.0f * PI * f0); /* quartz thickness in m */
    float n = f_n / f0; /* overtone number */

    /* Convert density from g/cm³ to kg/m³ */
    float rho_f_kg = p->density_g_cm3 * 1000.0f;

    cpx_t xi = voigt_load_impedance(f_n, p->thickness_nm * 1e-9f,
                                     p->viscosity_pa_s, p->shear_mod_pa,
                                     rho_f_kg, rho_l, eta_l);

    /* Δf/n = -Im(ξ) / (2π * ρq * tq) */
    *df_pred = -xi.im * n / (2.0f * PI * rho_q * tq);
    /* ΔD/n = -Re(ξ) / (π * f0 * ρq * tq) */
    *dd_pred = -xi.re * n / (PI * f0 * rho_q * tq);
}

/* Initialize Voigt parameters from Sauerbrey mass estimate */
void voigt_init_from_sauerbrey(voigt_params_t *p, float sauerbrey_mass_ng_cm2,
                               float rho_f_g_cm3)
{
    /* thickness = mass / (rho * 100) in nm */
    p->thickness_nm = sauerbrey_mass_ng_cm2 / (rho_f_g_cm3 * 100.0f);
    if (p->thickness_nm < 0.1f) p->thickness_nm = 0.1f;

    /* Initial guesses for viscoelastic properties */
    p->viscosity_pa_s = 0.001f;  /* water-like */
    p->shear_mod_pa = 1e5f;      /* soft gel */
    p->density_g_cm3 = rho_f_g_cm3;
    p->residual = 0;
    p->iterations = 0;
    p->converged = 0;
}

/* Levenberg-Marquardt fit of Voigt model to multi-overtone data.
 *
 * Parameters to fit: [d_f (nm), η_f (Pa·s), μ_f (Pa)]
 * ρ_f is assumed known (passed in via initial guess).
 */
voigt_params_t voigt_fit(const float *f_n, const float *df_n, const float *dd_n,
                         uint8_t n_ov, const float *rho_l_eta_l,
                         float f0, float rho_q, float mu_q)
{
    voigt_params_t result;
    memset(&result, 0, sizeof(result));

    float rho_l = rho_l_eta_l[0];
    float eta_l = rho_l_eta_l[1];

    /* Initial guess from Sauerbrey (use 3rd overtone, index 1) */
    float sauerbrey_mass = 0;
    if (n_ov > 1) {
        sauerbrey_mass = sauerbrey_mass(df_n[1], f_n[1], SAUERBREY_AREA_CM2);
    } else {
        sauerbrey_mass = sauerbrey_mass(df_n[0], f_n[0], SAUERBREY_AREA_CM2);
    }

    result.density_g_cm3 = 1.0f; /* assume water-like film density */
    voigt_init_from_sauerbrey(&result, sauerbrey_mass, result.density_g_cm3);

    /* LM parameters: [d_f, log10(η_f), log10(μ_f)]
     * Use log scale for η_f and μ_f since they span many orders of magnitude.
     */
    float p[3] = {
        result.thickness_nm,
        log10f(result.viscosity_pa_s),
        log10f(result.shear_mod_pa)
    };

    float lambda = 0.001f;
    uint16_t max_iter = 100;

    for (uint16_t iter = 0; iter < max_iter; iter++) {
        result.iterations = iter + 1;

        /* Compute predictions and residuals */
        float pred_df[QCM_OVERtones], pred_dd[QCM_OVERtones];
        voigt_params_t vp = result;
        vp.thickness_nm = p[0];
        vp.viscosity_pa_s = powf(10.0f, p[1]);
        vp.shear_mod_pa = powf(10.0f, p[2]);

        for (uint8_t i = 0; i < n_ov; i++) {
            voigt_predict(&vp, f_n[i], f0, rho_q, mu_q, rho_l, eta_l,
                          &pred_df[i], &pred_dd[i]);
        }

        /* Chi² */
        float chi2 = 0;
        for (uint8_t i = 0; i < n_ov; i++) {
            float rf = pred_df[i] - df_n[i];
            float rd = pred_dd[i] - dd_n[i];
            /* Weight: Δf typically ~100× larger than ΔD, normalize */
            chi2 += rf * rf + rd * rd * 1e12f; /* scale D to similar range */
        }

        /* Gradient and Hessian (3×3) */
        float grad[3] = {0, 0, 0};
        float hess[3][3] = {{0,0,0},{0,0,0},{0,0,0}};

        /* Numerical Jacobian via finite differences */
        float h = 1e-3f;
        for (uint8_t i = 0; i < n_ov; i++) {
            float Jf[3], Jd[3];
            for (int k = 0; k < 3; k++) {
                float p_p[3] = {p[0], p[1], p[2]};
                float p_m[3] = {p[0], p[1], p[2]};
                p_p[k] += h;
                p_m[k] -= h;

                voigt_params_t vpp = result, vpm = result;
                vpp.thickness_nm = p_p[0];
                vpp.viscosity_pa_s = powf(10.0f, p_p[1]);
                vpp.shear_mod_pa = powf(10.0f, p_p[2]);
                vpm.thickness_nm = p_m[0];
                vpm.viscosity_pa_s = powf(10.0f, p_m[1]);
                vpm.shear_mod_pa = powf(10.0f, p_m[2]);

                float pf_p, pd_p, pf_m, pd_m;
                voigt_predict(&vpp, f_n[i], f0, rho_q, mu_q, rho_l, eta_l, &pf_p, &pd_p);
                voigt_predict(&vpm, f_n[i], f0, rho_q, mu_q, rho_l, eta_l, &pf_m, &pd_m);

                Jf[k] = (pf_p - pf_m) / (2.0f * h);
                Jd[k] = (pd_p - pd_m) / (2.0f * h);
            }

            float rf = pred_df[i] - df_n[i];
            float rd = pred_dd[i] - dd_n[i];

            for (int a = 0; a < 3; a++) {
                grad[a] += Jf[a] * rf + Jd[a] * rd * 1e12f;
                for (int b = 0; b < 3; b++) {
                    hess[a][b] += Jf[a] * Jf[b] + Jd[a] * Jd[b] * 1e12f;
                }
            }
        }

        /* Augment Hessian */
        for (int a = 0; a < 3; a++)
            hess[a][a] *= (1.0f + lambda);

        /* Solve 3×3 normal equations */
        float aug[3][4];
        for (int a = 0; a < 3; a++) {
            for (int b = 0; b < 3; b++) aug[a][b] = hess[a][b];
            aug[a][3] = -grad[a]; /* -grad because we want to minimize */
        }

        /* Gaussian elimination */
        for (int a = 0; a < 3; a++) {
            if (fabsf(aug[a][a]) < 1e-30f) continue;
            for (int b = a + 1; b < 3; b++) {
                float factor = aug[b][a] / aug[a][a];
                for (int c = a; c <= 3; c++)
                    aug[b][c] -= factor * aug[a][c];
            }
        }

        /* Back substitution */
        float dp[3] = {0, 0, 0};
        for (int a = 2; a >= 0; a--) {
            dp[a] = aug[a][3];
            for (int b = a + 1; b < 3; b++)
                dp[a] -= aug[a][b] * dp[b];
            if (fabsf(aug[a][a]) > 1e-30f)
                dp[a] /= aug[a][a];
        }

        /* Trial step */
        float new_p[3] = {p[0] + dp[0], p[1] + dp[1], p[2] + dp[2]};

        /* Constrain: thickness > 0 */
        if (new_p[0] < 0.01f) new_p[0] = 0.01f;

        /* Compute new chi² */
        voigt_params_t vp_new = result;
        vp_new.thickness_nm = new_p[0];
        vp_new.viscosity_pa_s = powf(10.0f, new_p[1]);
        vp_new.shear_mod_pa = powf(10.0f, new_p[2]);

        float new_chi2 = 0;
        for (uint8_t i = 0; i < n_ov; i++) {
            float pf, pd;
            voigt_predict(&vp_new, f_n[i], f0, rho_q, mu_q, rho_l, eta_l, &pf, &pd);
            float rf = pf - df_n[i];
            float rd = pd - dd_n[i];
            new_chi2 += rf * rf + rd * rd * 1e12f;
        }

        if (new_chi2 < chi2) {
            p[0] = new_p[0]; p[1] = new_p[1]; p[2] = new_p[2];
            lambda *= 0.5f;
            if (lambda < 1e-8f) lambda = 1e-8f;
            if (fabsf(chi2 - new_chi2) / chi2 < 1e-6f) {
                result.converged = 1;
                break;
            }
        } else {
            lambda *= 10.0f;
            if (lambda > 1e8f) break;
        }
    }

    /* Store results */
    result.thickness_nm = p[0];
    result.viscosity_pa_s = powf(10.0f, p[1]);
    result.shear_mod_pa = powf(10.0f, p[2]);
    result.residual = 0; /* final chi2 could be computed */

    return result;
}