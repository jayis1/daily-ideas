/*
 * radiometry.h — DNI, AOD, PWV, Ångström exponent computation
 */

#ifndef RADIOMETRY_H
#define RADIOMETRY_H

#include <stdint.h>
#include <stdbool.h>
#include "stm32g474_conf.h"
#include "detector.h"

typedef struct {
    float dni[WL_COUNT];           /* DNI at each wavelength (W/m²) */
    float voltage[WL_COUNT];       /* Raw thermopile voltage (µV) */
    float aod[WL_COUNT];           /* Aerosol optical depth per wavelength */
    float angstrom_alpha;          /* Ångström exponent (440/870 nm fit) */
    float pwv_cm;                  /* Precipitable water vapor (cm) */
    float rayleigh[WL_COUNT];      /* Rayleigh optical depth per wavelength */
    float ozone_od[WL_COUNT];      /* Ozone optical depth per wavelength */
    float air_mass;                /* Relative optical air mass */
    float zenith_deg;              /* Solar zenith angle */
    float pressure_hpa;            /* Atmospheric pressure (hPa) */
    bool   valid;
} radiometry_result_t;

/* Compute AOD from measured voltages and Langley calibration constants.
 * Requires: V(λ) at each wavelength, V₀(λ) calibration, air mass, pressure.
 */
void radiometry_compute(radiometry_result_t *result,
                         const float voltages_uv[WL_COUNT],
                         const float v0_calibration[WL_COUNT],
                         double air_mass,
                         double zenith_deg,
                         float pressure_hpa,
                         float ozone_du);

/* Compute Ångström exponent from AOD at 440 and 870 nm */
float radiometry_angstrom(const float aod[WL_COUNT]);

/* Compute precipitable water vapor from 940 nm channel */
float radiometry_pwv(float v940, float v0_940, float aod940,
                      float air_mass);

/* Rayleigh optical depth: τ_R = 0.00864 × λ⁻⁴ × (P/P₀) */
float radiometry_rayleigh(float wavelength_nm, float pressure_hpa);

/* Ozone optical depth (climatology-based) */
float radiometry_ozone_od(float wavelength_nm, float ozone_du);

#endif /* RADIOMETRY_H */