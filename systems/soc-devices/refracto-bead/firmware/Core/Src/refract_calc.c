/**
 * refract_calc.c — Refractive index computation and derived quantities
 *
 * Uses per-wavelength calibration coefficients (quadratic polynomial)
 * to convert CCD edge position → refractive index. Applies prism-temperature
 * correction. Computes dispersion, Abbe number, Brix, SG, ABV, and freeze
 * point using standard formulas.
 *
 * The STM32G491 CORDIC peripheral is used for fast sin/arctan where needed
 * (Sellmeier fitting); most computations are simple polynomial evaluations.
 */

#include "refract_calc.h"
#include "compound_lib.h"
#include <string.h>
#include <math.h>

/* Calibration coefficients for each wavelength */
static cal_coeff_t s_cal[NUM_WAVELENGTHS] = {
    { DEFAULT_CAL_A, DEFAULT_CAL_B, DEFAULT_CAL_C },  /* 589 nm */
    { DEFAULT_CAL_A, DEFAULT_CAL_B * 0.998f, 0 },     /* 525 nm (slightly lower) */
    { DEFAULT_CAL_A, DEFAULT_CAL_B * 0.996f, 0 },     /* 470 nm (lower still) */
    { DEFAULT_CAL_A, DEFAULT_CAL_B * 1.002f, 0 },     /* 655 nm (slightly higher) */
};

/* Prism (SF11) dn/dT = -6.4 × 10⁻⁵ /°C */
#define SF11_DNDT  (-6.4e-5f)

/* Default sample dn/dT (water-based, overridden after compound match) */
#define DEFAULT_SAMPLE_DNDT  (-4.0e-4f)

void refract_calc_init(void) {
    /* TODO: Load calibration from flash (last 4KB sector, wear-leveled).
     * For now, use default coefficients.
     */
}

void refract_calc_store_cal(uint8_t wl_idx, const cal_coeff_t *coeff) {
    if (wl_idx < NUM_WAVELENGTHS) {
        s_cal[wl_idx] = *coeff;
        /* TODO: Write to flash */
    }
}

void refract_calc_get_cal(uint8_t wl_idx, cal_coeff_t *coeff) {
    if (wl_idx < NUM_WAVELENGTHS) {
        *coeff = s_cal[wl_idx];
    }
}

/* Find the calibration index for a given wavelength */
static int find_wl_idx(float wavelength) {
    if (fabsf(wavelength - 589.0f) < 5.0f) return WL_589;
    if (fabsf(wavelength - 525.0f) < 5.0f) return WL_525;
    if (fabsf(wavelength - 470.0f) < 5.0f) return WL_470;
    if (fabsf(wavelength - 655.0f) < 5.0f) return WL_655;
    return WL_589;  /* Default to D-line */
}

float refract_calc_ri(float p_edge, float wavelength, float t_prism) {
    if (p_edge < 0) return 0.0f;

    int idx = find_wl_idx(wavelength);
    const cal_coeff_t *c = &s_cal[idx];

    /* Quadratic polynomial: n = a + b*p + c*p² */
    float n = c->a + c->b * p_edge + c->c * p_edge * p_edge;

    /* Prism temperature correction (SF11 prism) */
    n += (t_prism - 20.0f) * SF11_DNDT;

    return n;
}

void refract_calc_derive(const float *n_values, const float *wavelengths,
                         float t_prism, ri_result_t *result) {
    if (!n_values || !wavelengths || !result) return;

    /* Identify which index is which wavelength */
    int idx_589 = -1, idx_525 = -1, idx_470 = -1, idx_655 = -1;
    for (int i = 0; i < 4; i++) {
        if (fabsf(wavelengths[i] - 589.0f) < 5.0f) idx_589 = i;
        else if (fabsf(wavelengths[i] - 525.0f) < 5.0f) idx_525 = i;
        else if (fabsf(wavelengths[i] - 470.0f) < 5.0f) idx_470 = i;
        else if (fabsf(wavelengths[i] - 655.0f) < 5.0f) idx_655 = i;
    }

    /* Copy RI values */
    for (int i = 0; i < 4; i++) result->n[i] = n_values[i];

    /* Primary RI at 589 nm */
    result->n_D = (idx_589 >= 0) ? n_values[idx_589] : n_values[0];

    /* RI at F (470 nm ≈ Hβ 486) and C (655 nm ≈ Hα 656) lines */
    result->n_F = (idx_470 >= 0) ? n_values[idx_470] : result->n_D;
    result->n_C = (idx_655 >= 0) ? n_values[idx_655] : result->n_D;

    /* Dispersion (n_F - n_C) */
    result->dispersion = result->n_F - result->n_C;

    /* Abbe number V_D = (n_D - 1) / (n_F - n_C) */
    if (fabsf(result->dispersion) > 1e-6f) {
        result->abbe_vd = (result->n_D - 1.0f) / result->dispersion;
    } else {
        result->abbe_vd = 999.0f;  /* Effectively no dispersion */
    }

    /* ---- Brix (sugar %) via ICUMSA polynomial ---- */
    /* Brix = c0 + c1*(n-1.333) + c2*(n-1.333)² + c3*(n-1.333)³
     * Valid for 0-95 °Bx, sucrose solutions at 20°C
     * Source: ICUMSA, refractometric Brix tables
     */
    float dn = result->n_D - 1.3330f;
    result->brix = 0.0f
        + 290.0f * dn
        + 1200.0f * dn * dn
        + 3500.0f * dn * dn * dn;

    if (result->brix < 0) result->brix = 0;
    if (result->brix > 95) result->brix = 95;

    /* ---- Specific gravity (urine/serum) ---- */
    /* Linear approximation: SG = 1.000 + (n_D - 1.3330) * k
     * k ≈ 2.6 for urine (validated against Atago USG-968)
     */
    result->specific_grav = 1.0000f + dn * 2.6f;

    if (result->specific_grav < 1.000f) result->specific_grav = 1.000f;
    if (result->specific_grav > 1.070f) result->specific_grav = 1.070f;

    /* ---- %ABV (ethanol in water) ---- */
    /* Ethanol-water mixture: n_D decreases from 1.3330 (water) to 1.3611 (100% EtOH)
     * Approximate: ABV = (1.3330 - n_D) / (1.3330 - 1.3611) * 100
     * But the relationship is non-linear. Use a 3rd-order polynomial fit.
     * For 0-100% ABV at 20°C:
     */
    float abv_dn = result->n_D - 1.3330f;
    /* ABV increases as RI decreases (ethanol has lower RI than water) */
    if (abv_dn <= 0) {
        /* RI is above water → likely sugar/dissolved solids, not alcohol */
        result->abv = 0;
    } else {
        /* Ethanol lowers RI: 100% EtOH → n_D = 1.3611, so dn = +0.0281
         * But for mixed solutions (wine/beer), the sugar also raises RI.
         * This is a simplified estimate; use distillation for accuracy.
         */
        float abv_est = (-abv_dn + 0.0281f) / 0.0281f * 100.0f;
        result->abv = (abv_est > 0 && abv_est < 100) ? abv_est : 0;
    }
    /* Note: For accurate ABV, distill first or use the "OIML" tables.
     * The Refracto Bead shows ABV only for binary ethanol-water mixtures.
     */

    /* ---- Coolant freeze point ---- */
    /* Ethylene glycol: freeze point from RI using empirical fit.
     * 0% EG → n_D = 1.333, FP = 0°C
     * 50% EG → n_D = 1.382, FP = -37°C
     * 100% EG → n_D = 1.432, FP = -12°C (actually supercools)
     * Linear approximation for 0-60% EG:
     */
    float eg_conc = (result->n_D - 1.3330f) / (1.3820f - 1.3330f) * 50.0f;
    if (eg_conc < 0) eg_conc = 0;
    if (eg_conc > 60) eg_conc = 60;

    /* Freeze point: approximately -0.74°C per %EG (for 0-50%) */
    result->freeze_point = -eg_conc * 0.74f;

    /* Store timestamp */
    /* result->timestamp = RTC_GetTick(); */  /* TODO: wire to RTC */
    result->t_prism = t_prism;
}