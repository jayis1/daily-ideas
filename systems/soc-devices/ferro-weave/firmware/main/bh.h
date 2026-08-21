/*
 * bh.h — B-H loop computation interface
 *
 * Pure-C computation of magnetic hysteresis loop quantities from sampled
 * H (field) and B (flux) arrays. Used by both the firmware (STM32G474)
 * and the host simulation build. The firmware version optionally uses the
 * STM32 CORDIC for the division/trig hot paths; this header exposes a
 * portable C fallback so the same code compiles on the host.
 */
#ifndef FERRO_WEAVE_BH_H
#define FERRO_WEAVE_BH_H

#include <stdint.h>
#include <stdbool.h>

/* Geometry / specimen parameters entered by the user. */
typedef struct {
    uint16_t n1;        /* primary turns                  */
    uint16_t n2;        /* secondary turns                */
    float    l_e;       /* magnetic path length  (m)      */
    float    a2;        /* secondary winding area (m^2)   */
    float    a_core;    /* specimen cross-section   (m^2) */
    float    rho;       /* material density       (kg/m^3)*/
    float    freq;      /* sweep frequency            (Hz)*/
} geom_t;

/* Computed loop result. */
typedef struct {
    float b_sat;        /* saturation flux density   (T)  */
    float h_c;          /* coercivity             (A/m)   */
    float b_r;          /* remanence                 (T)  */
    float mu_dc;        /* dc relative permeability       */
    float mu_inc_peak;  /* peak incremental permeability  */
    float p_v;          /* specific core loss     (W/kg)  */
    float squareness;   /* B_r / B_sat                    */
    float loop_area;    /* raw loop area (T·A/m)          */
    int   n_points;     /* samples in the loop            */
} bh_result_t;

/*
 * Compute the B-H loop result from n samples of H (A/m) and B (T).
 *
 * The arrays are assumed to cover one full magnetizing cycle at the peak
 * amplitude (the last cycle of the sweep). Air-flux correction is applied
 * to B in-place using the geometry's a2/a_core ratio.
 *
 * Returns 0 on success, -1 on invalid input.
 */
int bh_compute(const float *H, const float *B, int n,
               const geom_t *g, bh_result_t *out);

/* Apply air-flux correction: B_corr = B - mu0 * H * (A2-Acore)/A2 */
void bh_air_flux_correct(float *B, const float *H, int n, const geom_t *g);

/* Compute the loop area via the shoelace formula (T·A/m). */
float bh_loop_area(const float *H, const float *B, int n);

/* Find the B=0 crossing (returns H at that point, i.e. Hc). */
float bh_find_hc(const float *H, const float *B, int n);

/* Find the H=0 crossing (returns B at that point, i.e. Br). */
float bh_find_br(const float *H, const float *B, int n);

#endif /* FERRO_WEAVE_BH_H */