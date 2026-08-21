/*
 * pyro-balance / Core/Inc/tga.h
 * TG/DTG computation, step detection, kinetics.
 */
#ifndef TGA_H
#define TGA_H

#include "main.h"

#define TGA_MAX_SAMPLES 36000   /* 1 Hz × 10h = 36000 */
#define TGA_MAX_STEPS   8

typedef struct {
    bool    valid;
    float   onset_c;
    float   peak_c;
    float   endset_c;
    float   dmass_pct;     /* mass lost in this step (%) */
    float   dtg_peak_pct_per_min;
} tga_step_t;

typedef struct {
    float   temp_c[TGA_MAX_SAMPLES];
    float   mass_pct[TGA_MAX_SAMPLES];
    float   dtg_pct_per_min[TGA_MAX_SAMPLES];
    uint32_t n;
    float   m0_mg;                /* initial mass */
    float   residual_pct;         /* mass % at final temp */
    tga_step_t steps[TGA_MAX_STEPS];
    uint8_t  step_count;
} tga_run_t;

extern tga_run_t g_run;

void  tga_reset(float m0_mg);
void  tga_push(float temp_c, float mass_mg, uint32_t t_ms);
void  tga_finalize(void);           /* compute DTG, detect steps, residual */
const tga_run_t* tga_get(void);

/* Kissinger kinetics from multiple runs (same method_id, different rates) */
typedef struct {
    float beta;        /* heating rate (°C/min) */
    float tp_kelvin;   /* peak temperature (K) */
} kissinger_pt_t;

float tga_kissinger_E(const kissinger_pt_t* pts, uint8_t n);  /* J/mol */
float tga_ozawa_E(const kissinger_pt_t* pts, uint8_t n);

#endif /* TGA_H */