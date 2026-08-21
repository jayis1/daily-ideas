/*
 * volt-scribe — cv_engine.h
 * Cyclic Voltammetry engine interface
 */

#ifndef CV_ENGINE_H
#define CV_ENGINE_H

#include "main.h"

typedef struct {
    float cv_start;
    float cv_vertex;
    float cv_end;
    float cv_scan_rate;
    int   cv_cycles;
    float ir_compensation;
} params_t;

/* Reuse params_t from main.c — forward declaration */
struct params_t;
#define params_t params_t

void cv_run(const struct params_t *p);

extern float ir_comp_ohm;

#endif /* CV_ENGINE_H */