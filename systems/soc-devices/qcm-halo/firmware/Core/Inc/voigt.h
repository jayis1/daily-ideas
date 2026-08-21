/*
 * voigt.h — Voigt viscoelastic model fitting (Levenberg-Marquardt)
 */

#ifndef VOIGT_H
#define VOIGT_H

#include "config.h"

/* Voigt model parameters for a single viscoelastic layer on quartz */
typedef struct {
    float thickness_nm;   /* d_f       */
    float viscosity_pa_s; /* η_f       */
    float shear_mod_pa;   /* μ_f       */
    float density_g_cm3;  /* ρ_f       */
    float residual;       /* LM fit χ² */
    uint8_t iterations;
    uint8_t converged;
} voigt_params_t;

/* Fit Voigt model to multi-overtone Δf and ΔD data
 *
 * Inputs: arrays of overtone frequencies f[n], Δf[n], ΔD[n]
 * Outputs: fitted viscoelastic parameters
 *
 * Uses Levenberg-Marquardt with analytical Jacobian for the
 * Voigt model as described in:
 *   Voinova et al., Physica Scripta 59, 391 (1999)
 *
 * The model relates Δf and ΔD for each overtone n to the
 * viscoelastic properties of the film + semi-infinite liquid.
 */
voigt_params_t voigt_fit(const float *f_n, const float *df_n, const float *dd_n,
                         uint8_t n_overtones, const float *rho_l_eta_l,
                         float f0, float rho_q, float mu_q);

/* Initialize parameters from Sauerbrey estimate */
void voigt_init_from_sauerbrey(voigt_params_t *p, float sauerbrey_mass_ng_cm2,
                               float rho_f_g_cm3);

/* Compute theoretical Δf and ΔD for given Voigt params at overtone n */
void voigt_predict(const voigt_params_t *p, float f_n, float f0,
                   float rho_q, float mu_q,
                   float rho_l, float eta_l,
                   float *df_pred, float *dd_pred);

#endif /* VOIGT_H */