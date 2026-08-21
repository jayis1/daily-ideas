/**
 * refract_calc.h — Refractive index computation and derived quantities
 *
 * Converts CCD edge pixel positions to refractive index using per-wavelength
 * calibration coefficients (stored in flash). Computes:
 *   - n_D (RI at 589 nm)
 *   - n_F, n_C (RI at 470 and 655 nm for dispersion)
 *   - Abbe number V_D = (n_D - 1) / (n_F - n_C)
 *   - Brix (sugar %) via ICUMSA polynomial
 *   - Specific gravity (clinical urine)
 *   - %ABV (ethanol in water)
 *   - Freeze point (coolant concentration)
 */

#ifndef REFRACT_CALC_H
#define REFRACT_CALC_H

#include <stdint.h>

/* Wavelength indices */
#define WL_589   0   /* Sodium D-line */
#define WL_525   1   /* Green */
#define WL_470   2   /* Blue (≈ Hβ 486 nm) */
#define WL_655   3   /* Red (≈ Hα 656 nm) */

/* Number of calibration wavelengths */
#define NUM_WAVELENGTHS  4

/* Calibration coefficients: n = a + b*p + c*p² */
typedef struct {
    float a;   /* Offset */
    float b;   /* Linear coefficient */
    float c;   /* Quadratic coefficient (0 for linear fit) */
} cal_coeff_t;

/* Full measurement result */
typedef struct {
    /* Raw RI at each wavelength */
    float n[4];          /* n_589, n_525, n_470, n_655 */
    float n_D;           /* RI at 589 nm (primary) */
    float n_F;           /* RI at 470 nm (blue) */
    float n_C;           /* RI at 655 nm (red) */
    float dispersion;    /* n_F - n_C */
    float abbe_vd;       /* Abbe number V_D */

    /* Derived quantities */
    float brix;          /* Sugar content (°Bx) */
    float specific_grav; /* Specific gravity (urine/serum) */
    float abv;           /* Alcohol by volume (%) */
    float freeze_point;  /* Coolant freeze point (°C) */

    /* Temperatures */
    float t_prism;       /* Prism temperature (°C) */
    float t_ambient;     /* Ambient temperature (°C) */

    /* Compound identification */
    int8_t  compound_id;     /* Library index (-1 = unknown) */
    char    compound_name[16]; /* Name of best match */
    float   confidence;      /* 0.0–1.0 */

    /* Timestamp */
    uint32_t timestamp;   /* RTC tick */
} ri_result_t;

/**
 * Initialize refract_calc — load calibration from flash.
 */
void refract_calc_init(void);

/**
 * Convert a CCD edge pixel position to refractive index.
 *
 * @param p_edge      Sub-pixel edge position from edge_detect
 * @param wavelength  Wavelength in nm (589, 525, 470, 655)
 * @param t_prism     Prism temperature (°C) for correction
 * @return            Refractive index at the given wavelength
 */
float refract_calc_ri(float p_edge, float wavelength, float t_prism);

/**
 * Compute all derived quantities from 4-wavelength RI values.
 *
 * @param n_values    Array of 4 RI values (589, 525, 470, 655 nm)
 * @param wavelengths Array of 4 wavelengths (nm)
 * @param t_prism     Prism temperature (°C)
 * @param result      Output result structure (filled in)
 */
void refract_calc_derive(const float *n_values, const float *wavelengths,
                         float t_prism, ri_result_t *result);

/**
 * Store calibration coefficients for a wavelength.
 * Called during calibration procedure.
 */
void refract_calc_store_cal(uint8_t wl_idx, const cal_coeff_t *coeff);

/**
 * Get current calibration coefficients.
 */
void refract_calc_get_cal(uint8_t wl_idx, cal_coeff_t *coeff);

/* Default calibration (factory) — linear fit, will be overwritten
 * by 2-point calibration with water + RI standard oil.
 * These defaults assume:
 *   pixel 50 → n = 1.3330 (water)
 *   pixel 200 → n = 1.5150 (oil)
 * giving b = (1.5150 - 1.3330) / (200 - 50) = 0.0012133 / pixel
 */
#define DEFAULT_CAL_A   1.2723f
#define DEFAULT_CAL_B   0.0012133f
#define DEFAULT_CAL_C   0.0f

#endif /* REFRACT_CALC_H */