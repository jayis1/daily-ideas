/* wind.h — 3D wind vector computation and turbulence statistics */

#ifndef WIND_H
#define WIND_H

#include "sonic.h"

/* 3D wind vector */
typedef struct {
    float u;       /* east-west component (m/s) */
    float v;       /* north-south component (m/s) */
    float w;       /* vertical component (m/s) */
    float speed;   /* horizontal wind speed (m/s) */
    float direction; /* wind direction (degrees, meteorological) */
    float c_mean;  /* mean speed of sound (m/s) */
    float t_sonic; /* sonic temperature (K) */
} wind_vector_t;

/* Turbulence statistics over an averaging window */
typedef struct {
    float u_mean, v_mean, w_mean;
    float sigma_u, sigma_v, sigma_w;
    float u_w_cov;    /* ⟨u'w'⟩ momentum flux */
    float v_w_cov;    /* ⟨v'w'⟩ */
    float tke;        /* turbulent kinetic energy */
    float u_star;     /* friction velocity */
    float turb_intensity;  /* σ_u / ū */
    uint32_t n_samples;
} turbulence_stats_t;

/* Compute 3D wind vector from sonic sample */
void wind_compute(const sonic_sample_t *sample, wind_vector_t *wind);

/* Initialize turbulence accumulator (call at start of averaging window) */
void turb_init(turbulence_stats_t *stats);

/* Add a sample to turbulence accumulator */
void turb_add(turbulence_stats_t *stats, const wind_vector_t *wind);

/* Finalize turbulence statistics (compute means, std, cov, TKE) */
void turb_finalize(turbulence_stats_t *stats);

#endif /* WIND_H */