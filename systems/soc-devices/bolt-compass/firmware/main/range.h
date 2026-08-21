/*
 * range.h — Earth-ionosphere waveguide distance estimation
 */
#ifndef BOLT_COMPASS_RANGE_H
#define BOLT_COMPASS_RANGE_H

#include "types.h"

typedef enum {
    GROUND_OCEAN = 0,        /* σ = 4 S/m   (lowest attenuation) */
    GROUND_WET   = 1,        /* σ = 30 mS/m */
    GROUND_AVG   = 2,        /* σ = 10 mS/m (default, continental) */
    GROUND_DRY   = 3,        /* σ = 3 mS/m  */
    GROUND_ICE   = 4,        /* σ = 1 mS/m  (ice shield) */
} ground_t;

typedef struct {
    ground_t ground;
    int      daytime;        /* 1 = day (D-region high), 0 = night */
    float    ref_field_uv;   /* calibrated reference peak field at 100 km */
} range_model_t;

/* Estimate distance (km) from the sferic peak amplitude + propagation model. */
float range_estimate(const sferic_t *s, const range_model_t *m);

/* Default model (continental average, auto day/night from GPS hour). */
void range_defaults(range_model_t *m);

#endif /* BOLT_COMPASS_RANGE_H */