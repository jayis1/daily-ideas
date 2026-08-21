/*
 * radiometry.c — DNI, AOD, PWV, Ångström exponent computation
 *
 * Implements the Beer-Lambert-Bouguer law for aerosol optical depth
 * (AOD) retrieval from sun photometer measurements:
 *
 *   V(λ) = V₀(λ) × exp(-τ_total(λ) × m(θ))
 *   τ_aero(λ) = [ln(V₀) - ln(V)] / m - τ_Rayleigh - τ_ozone - τ_gas
 *
 * Also computes:
 *   - Ångström exponent: α = -ln(τ₁/τ₂) / ln(λ₁/λ₂)  (440/870 nm)
 *   - Precipitable water vapor (PWV) from 940 nm water vapor absorption
 *   - Rayleigh optical depth (molecular scattering)
 *   - Ozone optical depth (climatology)
 */

#include "radiometry.h"
#include "stm32g474_conf.h"
#include <math.h>

/* Wavelengths in meters for Rayleigh calculation */
static const float wavelengths_nm[WL_COUNT] = {
    405.0f, 440.0f, 675.0f, 870.0f, 940.0f, 1640.0f
};

/* Ozone absorption coefficients (cm⁻¹) per wavelength
 * Approximate values from IQUAM (Intercomparison of Quality-controlled
 * Urban Atmospheric Measurements) climatology.
 */
static const float ozone_abs_coef[WL_COUNT] = {
    0.000e-3f,   /* 405 nm — negligible */
    0.000e-3f,   /* 440 nm — negligible */
    0.050e-3f,   /* 675 nm — Chappuis band */
    0.000e-3f,   /* 870 nm — negligible */
    0.000e-3f,   /* 940 nm — negligible (water vapor dominates) */
    0.000e-3f,   /* 1640 nm — negligible */
};

/* Water vapor absorption coefficient at 940 nm (cm²/cm³)
 * This is an empirical coefficient; actual value depends on the
 * filter bandwidth and atmospheric conditions.
 */
#define WV_ABS_COEF_940   0.00654f

float radiometry_rayleigh(float wavelength_nm, float pressure_hpa)
{
    /* τ_R = 0.00864 × λ⁻⁴ × (P/P₀)
     * λ in µm, P in hPa, P₀ = 1013.25 hPa
     */
    float lambda_um = wavelength_nm / 1000.0f;
    float tau_r = RAYLEIGH_COEF * powf(lambda_um, -4.0f)
                * (pressure_hpa / P0_HPA);
    return tau_r;
}

float radiometry_ozone_od(float wavelength_nm, float ozone_du)
{
    /* τ_O3 = α_O3(λ) × U_O3
     * U_O3 in Dobson Units (DU); 1 DU = 0.001 cm NTP
     * α_O3 in cm⁻¹
     */
    float u_o3_cm = ozone_du * 0.001f;   /* DU to cm */
    for (int i = 0; i < WL_COUNT; i++) {
        if (wavelengths_nm[i] == wavelength_nm)
            return ozone_abs_coef[i] * u_o3_cm * 1000.0f;  /* scale factor */
    }
    return 0.0f;
}

float radiometry_angstrom(const float aod[WL_COUNT])
{
    /* α = -ln(τ(λ₁)/τ(λ₂)) / ln(λ₁/λ₂)
     * Use 440 nm (index 1) and 870 nm (index 3) — AERONET standard.
     */
    if (aod[WL_440] <= 0.0f || aod[WL_870] <= 0.0f)
        return 0.0f;

    float ratio = aod[WL_440] / aod[WL_870];
    float lambda_ratio = wavelengths_nm[WL_440] / wavelengths_nm[WL_870];
    float alpha = -logf(ratio) / logf(lambda_ratio);
    return alpha;
}

float radiometry_pwv(float v940, float v0_940, float aod940,
                      float air_mass)
{
    /* PWV = [ln(V₀) - ln(V) - τ_aero × m] / (m × k)
     * where k is the water vapor absorption coefficient.
     * At 940 nm, the AOD is mostly from water vapor + aerosol.
     * We subtract the aerosol contribution (estimated from 870 nm AOD).
     */
    if (v940 <= 0.0f || v0_940 <= 0.0f || air_mass <= 0.0f)
        return 0.0f;

    float ln_ratio = logf(v0_940) - logf(v940);
    float tau_aero_contribution = aod940 * (float)air_mass;
    float pwv = (ln_ratio - tau_aero_contribution)
              / ((float)air_mass * WV_ABS_COEF_940);
    if (pwv < 0.0f) pwv = 0.0f;
    return pwv;
}

void radiometry_compute(radiometry_result_t *result,
                         const float voltages_uv[WL_COUNT],
                         const float v0_calibration[WL_COUNT],
                         double air_mass,
                         double zenith_deg,
                         float pressure_hpa,
                         float ozone_du)
{
    result->air_mass = (float)air_mass;
    result->zenith_deg = (float)zenith_deg;
    result->pressure_hpa = pressure_hpa;

    for (int i = 0; i < WL_COUNT; i++) {
        /* Store raw voltage */
        result->voltage[i] = voltages_uv[i];

        /* Convert voltage to DNI (W/m²)
         * DNI = V / sensitivity (50 µV/(W/m²))
         * Note: voltage_uv is in µV, so DNI = voltage_uv / 50
         */
        result->dni[i] = voltages_uv[i] / (THERMOPILE_SENS * 1e6f);

        /* Rayleigh optical depth */
        result->rayleigh[i] = radiometry_rayleigh(wavelengths_nm[i],
                                                    pressure_hpa);

        /* Ozone optical depth */
        result->ozone_od[i] = radiometry_ozone_od(wavelengths_nm[i],
                                                    ozone_du);

        /* Total optical depth from Beer-Lambert:
         * τ_total = [ln(V₀) - ln(V)] / m
         * V₀ and V are in µV (same units, ratio is dimensionless)
         */
        if (voltages_uv[i] > 0.0f && v0_calibration[i] > 0.0f
            && air_mass > 0.0f) {
            float tau_total = (logf(v0_calibration[i])
                             - logf(voltages_uv[i])) / (float)air_mass;

            /* AOD = τ_total - τ_Rayleigh - τ_ozone */
            float aod = tau_total - result->rayleigh[i]
                       - result->ozone_od[i];
            if (aod < 0.0f) aod = 0.0f;   /* Clamp: can't be negative */
            result->aod[i] = aod;
        } else {
            result->aod[i] = 0.0f;
        }
    }

    /* Ångström exponent (440/870 nm) */
    result->angstrom_alpha = radiometry_angstrom(result->aod);

    /* Precipitable water vapor (940 nm) */
    /* Estimate aerosol at 940 nm from 870 nm AOD (Angstrom extrapolation) */
    float aod_940_est = result->aod[WL_870]
        * powf(wavelengths_nm[WL_870] / wavelengths_nm[WL_940],
               result->angstrom_alpha);
    result->pwv_cm = radiometry_pwv(voltages_uv[WL_940],
                                     v0_calibration[WL_940],
                                     aod_940_est,
                                     (float)air_mass);

    result->valid = true;
}