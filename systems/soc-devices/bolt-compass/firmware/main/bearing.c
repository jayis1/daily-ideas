/*
 * bearing.c — crossed-loop goniometer
 *
 *   V_NS = K · H · cos(α)        V_EW = K · H · sin(α)
 *      α = atan2(V_EW, V_NS)        (0 = North, clockwise)
 *
 * The 180° ambiguity (a single loop can't distinguish a stroke at α from
 * one at α+180°) is resolved by the sign of the initial E-field change:
 * a CG stroke that lowers negative charge to ground produces a ΔE of a
 * known sign relative to the bearing. Convention:
 *
 *   if e_sign > 0  → the nearer half (no flip)
 *   if e_sign < 0  → the farther half (flip by 180°)
 *   if e_sign == 0 → ambiguous; leave as-is, mark low confidence upstream
 */
#include "bearing.h"
#include <math.h>

float bearing_compute(const sferic_t *s)
{
    float ns = s->peak_ns;
    float ew = s->peak_ew;
    float az = atan2f(ew, ns) * (180.0f / (float)M_PI);
    if (az < 0) az += 360.0f;

    /* Resolve 180° ambiguity with the E-field sign. */
    if (s->e_sign < 0) {
        az += 180.0f;
        if (az >= 360.0f) az -= 360.0f;
    }
    /* e_sign == 0 → leave azimuth as the "near" guess. */
    return az;
}