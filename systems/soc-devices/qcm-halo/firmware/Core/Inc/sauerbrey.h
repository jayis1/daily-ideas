/*
 * sauerbrey.h — Sauerbrey mass + Kanazawa-Gordon liquid analysis
 */

#ifndef SAUERBREY_H
#define SAUERBREY_H

#include "config.h"

/* Sauerbrey: Δm = -Δf / S,  S = 2*f0²/(A*sqrt(ρq*μq))
 * Returns mass in ng/cm² (areal mass density).
 */
float sauerbrey_mass(float delta_f_hz, float f0_hz, float area_cm2);

/* Sauerbrey thickness in nm, given film density ρ_f in g/cm³ */
float sauerbrey_thickness_ng_cm2_to_nm(float mass_ng_cm2, float rho_f_g_cm3);

/* Kanazawa-Gordon: Δf = -f0^(3/2) * sqrt(ρl*ηl / (π*ρq*μq))
 * For a crystal in contact with a Newtonian liquid.
 */
float kanazawa_delta_f(float f0_hz, float rho_l_kg_m3, float eta_l_pa_s);

/* Inverse: given measured Δf in liquid, compute ρl*ηl product */
float kanazawa_rho_eta(float f0_hz, float delta_f_hz);

/* D-factor ratio: ΔD/Δf — indicates film rigidity
 * < 0.4e-6/Hz: rigid (Sauerbrey valid)
 * > 0.4e-6/Hz: viscoelastic (needs Voigt model)
 */
float d_to_f_ratio(float delta_d, float delta_f);
int   is_sauerbrey_valid(float delta_d, float delta_f);

#endif /* SAUERBREY_H */