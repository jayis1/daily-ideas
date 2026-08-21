/*
 * visco-shear / firmware / rheology.c
 * Rheological model fitting (Levenberg-Marquardt) + viscosity computation
 *
 * Models: Newtonian, Power-Law, Bingham, Herschel-Bulkley, Casson, Cross, Carreau
 * Fitting: nonlinear least-squares via Levenberg-Marquardt.
 * Model selection: lowest AIC.
 *
 * MIT License.
 */
#include <math.h>
#include <string.h>
#include "pico/stdlib.h"
#include "main.h"
#include "rheology.h"
#include "spindle.h"

const char *model_names[MODEL_COUNT] = {
    "Newtonian", "Power-Law", "Bingham", "Herschel-Bulkley",
    "Casson", "Cross", "Carreau"
};

/* ── Model functions: τ = f(γ̇, params) ────────────────────────── */

static float model_newtonian(float gd, const float *p)
{
    /* p[0] = η (Pa·s) */
    return p[0] * gd;
}

static float model_power_law(float gd, const float *p)
{
    /* p[0] = K, p[1] = n */
    return p[0] * powf(gd, p[1]);
}

static float model_bingham(float gd, const float *p)
{
    /* p[0] = τ_B (Pa), p[1] = η_p (Pa·s) */
    float tau = p[0] + p[1] * gd;
    return (tau > 0) ? tau : 0;
}

static float model_herschel_bulkley(float gd, const float *p)
{
    /* p[0] = τ_HB, p[1] = K, p[2] = n */
    float tau = p[0] + p[1] * powf(gd, p[2]);
    return (tau > 0) ? tau : p[0];
}

static float model_casson(float gd, const float *p)
{
    /* p[0] = τ_C, p[1] = η_C */
    float sq_tau = sqrtf(p[0]) + sqrtf(p[1] * gd);
    return sq_tau * sq_tau;
}

static float model_cross(float gd, const float *p)
{
    /* p[0] = η_0, p[1] = η_∞, p[2] = λ, p[3] = m */
    float denom = 1.0f + powf(p[2] * gd, p[3]);
    return p[1] + (p[0] - p[1]) / denom;
}

static float model_carreau(float gd, const float *p)
{
    /* p[0] = η_0, p[1] = η_∞, p[2] = λ, p[3] = n */
    float denom = powf(1.0f + powf(p[2] * gd, 2.0f), p[3] / 2.0f);
    return p[1] + (p[0] - p[1]) / denom;
}

typedef float (*model_fn_t)(float, const float *);

static const model_fn_t model_fns[MODEL_COUNT] = {
    model_newtonian, model_power_law, model_bingham, model_herschel_bulkley,
    model_casson, model_cross, model_carreau
};

static const int model_n_params[MODEL_COUNT] = {1, 2, 2, 3, 2, 4, 4};

/* ── Residual & Jacobian ───────────────────────────────────────── */

static float compute_residual(const measure_result_t *res, model_fn_t fn,
                              const float *params, float *residuals)
{
    float ss = 0;
    for (int i = 0; i < res->n_points; i++) {
        float tau_measured = res->torque[i] * 1e-6f /
                             spindle_torque_to_stress_factor(res->spindle);
        float tau_model = fn(res->shear_rate[i], params);
        residuals[i] = tau_measured - tau_model;
        ss += residuals[i] * residuals[i];
    }
    return ss;
}

/* Numerical Jacobian (finite difference) */
static void compute_jacobian(const measure_result_t *res, model_fn_t fn,
                             const float *params, int n_params,
                             float *jac, float *residuals)
{
    float h = 1e-6f;
    float *p_tmp = (float *)malloc(n_params * sizeof(float));
    for (int j = 0; j < n_params; j++) {
        memcpy(p_tmp, params, n_params * sizeof(float));
        p_tmp[j] += h;
        for (int i = 0; i < res->n_points; i++) {
            float tau_measured = res->torque[i] * 1e-6f /
                                 spindle_torque_to_stress_factor(res->spindle);
            float f_plus = fn(res->shear_rate[i], p_tmp);
            jac[i * n_params + j] = -(f_plus - fn(res->shear_rate[i], params)) / h;
        }
    }
    free(p_tmp);
    /* Recompute residuals at current params */
    compute_residual(res, fn, params, residuals);
}

/* ── Levenberg-Marquardt fit ───────────────────────────────────── */

static float lm_fit(const measure_result_t *res, model_fn_t fn,
                    int n_params, float *params, int max_iter)
{
    float lambda = 1e-3f;
    float *residuals = (float *)malloc(res->n_points * sizeof(float));
    float *jac = (float *)malloc(res->n_points * n_params * sizeof(float));
    float *jtj = (float *)malloc(n_params * n_params * sizeof(float));
    float *jtr = (float *)malloc(n_params * sizeof(float));
    float *delta = (float *)malloc(n_params * sizeof(float));
    float *params_new = (float *)malloc(n_params * sizeof(float));

    float ss = compute_residual(res, fn, params, residuals);

    for (int iter = 0; iter < max_iter; iter++) {
        compute_jacobian(res, fn, params, n_params, jac, residuals);

        /* Build J^T J and J^T r */
        for (int j = 0; j < n_params; j++) {
            jtr[j] = 0;
            for (int k = 0; k < n_params; k++) {
                jtj[j * n_params + k] = 0;
            }
        }
        for (int i = 0; i < res->n_points; i++) {
            for (int j = 0; j < n_params; j++) {
                jtr[j] += jac[i * n_params + j] * residuals[i];
                for (int k = 0; k < n_params; k++) {
                    jtj[j * n_params + k] += jac[i * n_params + j] * jac[i * n_params + k];
                }
            }
        }

        /* Solve (J^T J + λ·diag) δ = J^T r via Gaussian elimination */
        int n = n_params;
        float aug[8][9];  /* Max 4 params + RHS */
        for (int j = 0; j < n; j++) {
            for (int k = 0; k < n; k++) {
                aug[j][k] = jtj[j * n + k];
                if (j == k) aug[j][k] += lambda * jtj[j * n + k];
            }
            aug[j][n] = jtr[j];
        }

        /* Gaussian elimination with partial pivoting */
        for (int j = 0; j < n; j++) {
            int piv = j;
            for (int k = j + 1; k < n; k++) {
                if (fabsf(aug[k][j]) > fabsf(aug[piv][j])) piv = k;
            }
            if (piv != j) {
                for (int k = 0; k <= n; k++) {
                    float tmp = aug[j][k]; aug[j][k] = aug[piv][k]; aug[piv][k] = tmp;
                }
            }
            if (fabsf(aug[j][j]) < 1e-15f) continue;
            for (int k = j + 1; k < n; k++) {
                float factor = aug[k][j] / aug[j][j];
                for (int m = j; m <= n; m++) {
                    aug[k][m] -= factor * aug[j][m];
                }
            }
        }

        /* Back-substitution */
        for (int j = n - 1; j >= 0; j--) {
            delta[j] = aug[j][n];
            for (int k = j + 1; k < n; k++) {
                delta[j] -= aug[j][k] * delta[k];
            }
            delta[j] /= (fabsf(aug[j][j]) > 1e-15f) ? aug[j][j] : 1e-15f;
        }

        /* Try new parameters */
        for (int j = 0; j < n_params; j++) {
            params_new[j] = params[j] + delta[j];
            /* Clamp to physical ranges */
            if (params_new[j] < 0) params_new[j] = 1e-6f;
        }

        float ss_new = compute_residual(res, fn, params_new, residuals);

        if (ss_new < ss) {
            /* Accept */
            for (int j = 0; j < n_params; j++) params[j] = params_new[j];
            ss = ss_new;
            lambda *= 0.7f;
            if (lambda < 1e-10f) lambda = 1e-10f;
        } else {
            lambda *= 2.0f;
            if (lambda > 1e6f) break;
        }
    }

    free(residuals); free(jac); free(jtj); free(jtr);
    free(delta); free(params_new);
    return ss;
}

/* ── Fit all models and select best ────────────────────────────── */

void rheology_fit_models(measure_result_t *res)
{
    model_fit_t fits[MODEL_COUNT];

    for (int m = 0; m < MODEL_COUNT; m++) {
        int np = model_n_params[m];
        float params[4] = {0};

        /* Initial guesses */
        switch (m) {
        case MODEL_NEWTONIAN:
            params[0] = (res->n_points > 0 && res->shear_rate[0] > 0) ?
                        res->viscosity[0] / 1000.0f : 0.1f;
            break;
        case MODEL_POWER_LAW:
            params[0] = 0.1f; params[1] = 1.0f;  /* K, n */
            break;
        case MODEL_BINGHAM:
            params[0] = 0.5f; params[1] = 0.01f;  /* τ_B, η_p */
            break;
        case MODEL_HERSCHEL_BULKLEY:
            params[0] = 0.1f; params[1] = 0.1f; params[2] = 0.8f;
            break;
        case MODEL_CASSON:
            params[0] = 0.1f; params[1] = 0.01f;
            break;
        case MODEL_CROSS:
            params[0] = 1.0f; params[1] = 0.001f; params[2] = 0.1f; params[3] = 0.8f;
            break;
        case MODEL_CARREAU:
            params[0] = 1.0f; params[1] = 0.001f; params[2] = 0.1f; params[3] = 0.8f;
            break;
        }

        float ss = lm_fit(res, model_fns[m], np, params, 50);

        /* Compute R² */
        float mean_tau = 0;
        for (int i = 0; i < res->n_points; i++)
            mean_tau += res->torque[i] * 1e-6f / spindle_torque_to_stress_factor(res->spindle);
        mean_tau /= res->n_points;

        float ss_tot = 0;
        for (int i = 0; i < res->n_points; i++) {
            float dev = res->torque[i] * 1e-6f / spindle_torque_to_stress_factor(res->spindle) - mean_tau;
            ss_tot += dev * dev;
        }
        fits[m].model = (rheo_model_t)m;
        fits[m].r_squared = (ss_tot > 0) ? (1.0f - ss / ss_tot) : 0;
        fits[m].aic = res->n_points * logf(ss / res->n_points + 1e-15f) + 2 * np;
        memcpy(fits[m].param, params, np * sizeof(float));
    }

    /* Select best model by AIC */
    int best = 0;
    for (int m = 1; m < MODEL_COUNT; m++) {
        if (fits[m].aic < fits[best].aic) best = m;
    }
    res->best_fit = fits[best];
}

void rheology_print_fit(const model_fit_t *fit)
{
    printf("Model: %s\n", model_names[fit->model]);
    printf("  R² = %.5f, AIC = %.2f\n", fit->r_squared, fit->aic);
    int np = model_n_params[fit->model];
    for (int i = 0; i < np; i++) {
        printf("  p[%d] = %.6f\n", i, fit->param[i]);
    }
}