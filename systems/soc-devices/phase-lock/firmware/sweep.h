/*
 * sweep.h — frequency and amplitude sweep engine
 */
#ifndef SWEEP_H
#define SWEEP_H

#include <stdint.h>
#include <stdbool.h>
#include "demod.h"

typedef enum { SWEEP_FREQ, SWEEP_AMP, SWEEP_NONE } sweep_mode_t;

typedef struct {
    sweep_mode_t mode;
    float f_start, f_stop;
    float a_start, a_stop;
    uint16_t n_points;
    bool   log_spacing;
    uint16_t cur_point;
    bool    running;
} sweep_state_t;

void sweep_init(void);
void sweep_start_freq(float f1, float f2, uint16_t n, bool logspace);
void sweep_start_amp(float a1, float a2, uint16_t n);
void sweep_stop(void);
bool sweep_step(void);   /* advance one point; returns false when done */
bool sweep_running(void);
uint16_t sweep_point(void);
uint16_t sweep_npoints(void);
float sweep_current_freq(void);
float sweep_current_amp(void);

/* Per-point record (saved to SD) */
typedef struct {
    float    f;        /* Hz    */
    float    a;        /* V     */
    float    R;        /* magnitude (V) */
    float    theta;    /* phase (rad) */
    float    X;        /* in-phase (V) */
    float    Y;        /* quadrature (V) */
    float    noise;    /* V/√Hz */
    uint32_t ts_ms;   /* timestamp (ms) */
} sweep_point_t;

/* Retrieve the latest point record (after sweep_step returns true) */
sweep_point_t sweep_last_point(void);

extern sweep_state_t g_sweep;

#endif /* SWEEP_H */