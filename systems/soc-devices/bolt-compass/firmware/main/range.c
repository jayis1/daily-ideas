/*
 * range.c — Earth-ionosphere waveguide distance estimation
 *
 * The sferic peak E-field decays with distance d roughly as:
 *
 *   E_peak(d) ≈ E_ref · exp(−α · d) / sqrt(d / d_ref)
 *
 * where α is the mode-1 TM attenuation rate (per km) at ~10 kHz, which
 * depends on ground conductivity (σ_g) and ionosphere day/night.
 *
 * We invert this numerically (Newton, 4 iterations) to recover d from
 * the measured peak. The peak amplitude from the two loops is converted
 * to an equivalent E-field (µV/m) using the calibrated ref_field_uv,
 * which is set during the calibration step (cross-correlation with the
 * Blitzortung feed — see scripts/storm_view.py --calibrate).
 *
 * Tabulated α (per km) at 10 kHz, mode-1 TM, from Wait & Spies 1964:
 *
 *   ground conductivity  |  day α   |  night α
 *   OCEAN (4 S/m)        |  0.00018 |  0.00010
 *   WET   (30 mS/m)      |  0.00040 |  0.00020
 *   AVG   (10 mS/m)      |  0.00075 |  0.00035
 *   DRY   (3 mS/m)       |  0.00140 |  0.00070
 *   ICE   (1 mS/m)       |  0.00220 |  0.00110
 */
#include "range.h"
#include <math.h>

static const float ALPHA[5][2] = {
    { 0.00018f, 0.00010f },   /* OCEAN */
    { 0.00040f, 0.00020f },   /* WET   */
    { 0.00075f, 0.00035f },   /* AVG   */
    { 0.00140f, 0.00070f },   /* DRY   */
    { 0.00220f, 0.00110f },   /* ICE   */
};

void range_defaults(range_model_t *m)
{
    m->ground       = GROUND_AVG;
    m->daytime      = 1;
    m->ref_field_uv = 1000.0f;   /* 1000 µV/m at 100 km reference (calibrate) */
}

float range_estimate(const sferic_t *s, const range_model_t *m)
{
    /* Loop peak amplitude → equivalent E-field (µV/m).
     * Loop calibration constant: E ≈ peak / K_loop, K_loop set so that
     * a 1000 µV/m sferic at 100 km gives peak=4096 (full scale). */
    const float K_LOOP = 4.096f;   /* peak units per µV/m (calibrate) */
    float e_meas = sqrtf(s->peak_ns * s->peak_ns +
                         s->peak_ew * s->peak_ew) / K_LOOP;
    if (e_meas < 1.0f) return 9999.0f;   /* too weak to range */

    float alpha = ALPHA[m->ground][m->daytime ? 0 : 1];
    float d_ref = 100.0f;                 /* km */
    float e_ref = m->ref_field_uv;

    /* Solve  e_meas = e_ref · exp(−α·d) · sqrt(d_ref / d)  for d.
     * Newton on f(d) = ln(e_meas/e_ref) + α·d + 0.5·ln(d/d_ref) = 0. */
    float d = 50.0f;                      /* initial guess 50 km */
    for (int i = 0; i < 6; i++) {
        float f  = logf(e_meas / e_ref) + alpha * d + 0.5f * logf(d / d_ref);
        float df = alpha + 0.5f / d;
        d -= f / df;
        if (d < 1.0f) d = 1.0f;
    }
    if (d > 3000.0f) d = 3000.0f;
    return d;
}