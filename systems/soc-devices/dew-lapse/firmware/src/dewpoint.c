/* dewpoint.c — psychrometric conversion functions
 *
 * Implements:
 *   - Magnus-Tetens saturation vapor pressure (Sonntag94 coefficients)
 *   - Dew/frost point → RH, absolute humidity, mixing ratio
 *   - Phase-aware (liquid water / ice) per WMO convention
 */
#include "dewpoint.h"
#include <math.h>

/* Sonntag94 Magnus coefficients.
 *  over water: e_s = 6.1164 * exp(17.625*T / (243.04 + T))  [hPa]
 *  over ice:   e_s = 6.1092 * exp(21.875*T / (265.5  + T))  [hPa]
 */
float sat_vapor_pressure_hpa(float t_c, int over_water)
{
    if (over_water) {
        return 6.116441f * expf(17.625f * t_c / (243.04f + t_c));
    } else {
        return 6.109217f * expf(21.875f * t_c / (265.5f + t_c));
    }
}

void humidity_compute(humidity_t *h, float t_mirror, float t_air,
                      float p_pa, int is_ice)
{
    /* Vapor pressure at the dew/frost point is the saturation vapor
     * pressure evaluated at the mirror temperature. */
    float e = sat_vapor_pressure_hpa(t_mirror, !is_ice);   /* hPa */
    float es_air = sat_vapor_pressure_hpa(t_air, 1);       /* over water */

    h->e_hpa  = e;
    h->dew_c  = t_mirror;
    h->rh_pct = 100.0f * e / es_air;
    if (h->rh_pct < 0.0f)   h->rh_pct = 0.0f;
    if (h->rh_pct > 100.0f) h->rh_pct = 100.0f;

    /* Absolute humidity [g/m³] = 216.7 * e_hPa / (T_K) */
    h->ah_gm3 = 216.7f * e / (t_air + 273.15f);

    /* Mixing ratio [g/kg dry air] = 622 * e / (P - e) */
    float p_hpa = p_pa / 100.0f;
    h->w_gkg = 622.0f * e / (p_hpa - e);

    h->phase = is_ice ? 1 : 0;
    h->valid = 1;
}