/*
 * sweep.h — programmable magnetizing-current sweep generator
 */
#ifndef FERRO_WEAVE_SWEEP_H
#define FERRO_WEAVE_SWEEP_H

#include <stdint.h>
#include <stdbool.h>
#include "bh.h"

typedef enum {
    SWEEP_SIN  = 0,   /* sinusoidal current      */
    SWEEP_TRI  = 1,   /* triangular current      */
    SWEEP_DC   = 2,   /* quasi-DC slow ramp      */
} sweep_waveform_t;

typedef struct {
    sweep_waveform_t waveform;
    float  i_peak;      /* peak magnetizing current (A)        */
    float  freq;        /* sweep frequency             (Hz)    */
    uint16_t ramp_cycles; /* amplitude ramp-up cycles         */
    uint16_t hold_cycles; /* cycles at peak amplitude         */
    bool   degauss;     /* run degauss before the sweep       */
} sweep_params_t;

typedef enum {
    SWEEP_IDLE = 0,
    SWEEP_DEGAUSS,
    SWEEP_ARM,
    SWEEP_RAMP,
    SWEEP_HOLD,
    SWEEP_CAPTURE,
    SWEEP_COMPUTE,
    SWEEP_LOG,
    SWEEP_DISARM,
    SWEEP_DONE,
    SWEEP_FAULT,
} sweep_state_t;

/* Default sweep parameters. */
void sweep_defaults(sweep_params_t *p);

/* Kick off a measurement cycle. Returns 0 on success. */
int  sweep_start(const sweep_params_t *p);

/* Current sweep state. */
sweep_state_t sweep_get_status(void);

/* Stop immediately (also called by the hardware fault handler). */
void sweep_stop(void);

/* Generate one cycle of the sweep waveform into out[] (length n).
 * amp is the fractional amplitude [0..1] of i_peak. Used by the sim
 * and by the HRTIM DAC/comparator configuration in firmware. */
void sweep_gen_cycle(const sweep_params_t *p, float amp,
                     float *out, int n);

/* Generate an exponential-decay degauss envelope (amp vs cycle index). */
void sweep_gen_degauss(float *amps, int n_cycles);

#endif /* FERRO_WEAVE_SWEEP_H */