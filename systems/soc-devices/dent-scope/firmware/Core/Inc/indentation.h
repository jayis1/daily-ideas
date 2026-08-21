/*
 * dent-scope / Core/Inc/indentation.h
 * Dent Scope — Oliver–Pharr instrumented indentation analysis
 * MIT License.
 */
#ifndef INDENTATION_H
#define INDENTATION_H

#include "main.h"

#define INDENT_MAX_POINTS 6000   /* 500 Hz × 12 s max test */

typedef struct {
    float force_mN[INDENT_MAX_POINTS];
    float depth_um[INDENT_MAX_POINTS];
    int   count;
    /* computed results */
    float S_mN_um;      /* contact stiffness dP/dh at peak */
    float h_contact_um; /* contact depth h_c */
    float area_um2;     /* contact area A(h_c) */
    float hardness_MPa; /* H = P_max / A */
    float E_r_GPa;      /* reduced modulus */
    float E_GPa;        /* Young's modulus (diamond-corrected) */
    float W_total_nJ;   /* total work (loading curve area) */
    float W_elastic_nJ; /* elastic work (unloading curve area) */
    float eta;          /* W_elastic / W_total */
} indent_result_t;

void indent_result_init(void);
void indentation_init(void);
void indentation_reset(void);
void indentation_push(float force_mN, float depth_um);
void indentation_finalize(void);
void indentation_compute(ds_status_t *st);
indent_result_t *indentation_get(void);

#endif /* INDENTATION_H */