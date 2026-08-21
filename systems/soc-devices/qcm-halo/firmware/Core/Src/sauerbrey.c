/*
 * sauerbrey.c — Sauerbrey mass + Kanazawa-Gordon liquid analysis
 */

#include "main.h"
#include <math.h>
#include "sauerbrey.h"

/* Sauerbrey equation:
 *   Δf = -(2 * f0² * Δm) / (A * sqrt(ρq * μq))
 *   Δm = -Δf * A * sqrt(ρq * μq) / (2 * f0²)
 *
 * Δm in kg, A in m², f0 in Hz.
 * We return areal mass density in ng/cm².
 */
float sauerbrey_mass(float delta_f_hz, float f0_hz, float area_cm2)
{
    /* sqrt(ρq * μq) = sqrt(2650 * 2.947e10) = sqrt(7.81e13) = 8.837e6 */
    float sqrt_rq_muq = sqrtf(QUARTZ_DENSITY * QUARTZ_SHEAR_MOD);
    float area_m2 = area_cm2 * 1e-4f; /* cm² → m² */

    /* Δm in kg */
    float dm_kg = -delta_f_hz * area_m2 * sqrt_rq_muq / (2.0f * f0_hz * f0_hz);

    /* Convert kg/m² to ng/cm²:
     * 1 kg = 1e12 ng, 1 m² = 1e4 cm² → kg/m² = 1e8 ng/cm²
     */
    return dm_kg * 1e8f;
}

/* Convert areal mass (ng/cm²) to thickness (nm)
 * mass_ng_cm2 / (rho_g_cm3 * 1e-6) → thickness in nm
 * (1 cm² * 1 nm = 1e-7 cm³, density g/cm³ → mass = rho * 1e-7 g = rho * 100 ng)
 * So thickness_nm = mass_ng_cm2 / (rho_g_cm3 * 100)
 */
float sauerbrey_thickness_ng_cm2_to_nm(float mass_ng_cm2, float rho_f_g_cm3)
{
    if (rho_f_g_cm3 <= 0) return 0;
    return mass_ng_cm2 / (rho_f_g_cm3 * 100.0f);
}

/* Kanazawa-Gordon equation for a crystal in contact with a Newtonian liquid:
 *   Δf = -f0^(3/2) * sqrt(ρl * ηl / (π * ρq * μq))
 */
float kanazawa_delta_f(float f0_hz, float rho_l_kg_m3, float eta_l_pa_s)
{
    float factor = sqrtf(rho_l_kg_m3 * eta_l_pa_s /
                         (PI * QUARTZ_DENSITY * QUARTZ_SHEAR_MOD));
    return -powf(f0_hz, 1.5f) * factor;
}

/* Inverse Kanazawa-Gordon: compute ρl*ηl from measured Δf */
float kanazawa_rho_eta(float f0_hz, float delta_f_hz)
{
    /* Δf = -f0^1.5 * sqrt(ρl*ηl / (π*ρq*μq))
     * (Δf/f0^1.5)² = ρl*ηl / (π*ρq*μq)
     * ρl*ηl = (Δf/f0^1.5)² * π * ρq * μq
     */
    float ratio = delta_f_hz / powf(f0_hz, 1.5f);
    return ratio * ratio * PI * QUARTZ_DENSITY * QUARTZ_SHEAR_MOD;
}

/* ΔD/Δf ratio — indicator of film rigidity */
float d_to_f_ratio(float delta_d, float delta_f)
{
    if (fabsf(delta_f) < 1e-6f) return 0;
    return delta_d / delta_f;
}

/* Rule of thumb: if |ΔD/Δf| < 0.4e-6/Hz, film is "rigid" → Sauerbrey valid
 * (Some use 1e-6/Hz, we use the more conservative 0.4e-6/Hz)
 */
int is_sauerbrey_valid(float delta_d, float delta_f)
{
    if (fabsf(delta_f) < 0.1f) return 1; /* no mass change, trivially valid */
    float ratio = fabsf(delta_d / delta_f);
    return (ratio < 0.4e-6f) ? 1 : 0;
}