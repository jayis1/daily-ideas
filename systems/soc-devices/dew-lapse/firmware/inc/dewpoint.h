/* dewpoint.h — psychrometric conversion functions */
#ifndef DEWPOINT_H
#define DEWPOINT_H

#include <stdint.h>

typedef struct {
    float dew_c;        /* dew (or frost) point, °C */
    float rh_pct;        /* relative humidity, % */
    float ah_gm3;        /* absolute humidity, g/m³ */
    float w_gkg;         /* mixing ratio, g/kg dry air */
    float e_hpa;         /* vapor pressure, hPa */
    int   phase;         /* 0 = liquid dew, 1 = frost/ice */
    int   valid;         /* 1 if equilibrium reached */
} humidity_t;

/* Compute humidity quantities from mirror temperature (dew/frost) and
 * ambient air temperature + pressure.
 *   t_mirror : equilibrium mirror temperature [°C]
 *   t_air    : ambient air temperature [°C]
 *   p_pa     : total atmospheric pressure [Pa]
 *   is_ice   : 1 if phase is frost (sub-0 °C condensate)
 */
void humidity_compute(humidity_t *h, float t_mirror,
                      float t_air, float p_pa, int is_ice);

/* Magnus-Tetens saturation vapor pressure (hPa). over_water=1 → over water,
 * over_water=0 → over ice (Buck/ Sonntag94 coefficients). */
float sat_vapor_pressure_hpa(float t_c, int over_water);

#endif