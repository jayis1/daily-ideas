/*
 * sweep.c — programmable magnetizing-current sweep generator
 *
 * Generates the waveform samples that drive the HRTIM/DAC and the
 * amplitude envelope for the ramp-up + hold + capture sequence. The
 * firmware maps these to HRTIM duty-cycle updates; the simulation uses
 * them directly to synthesise the H and B arrays.
 */
#include "sweep.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

void sweep_defaults(sweep_params_t *p)
{
    p->waveform     = SWEEP_SIN;
    p->i_peak       = 1.0f;     /* ±1 A                                  */
    p->freq         = 10.0f;    /* 10 Hz — good for soft magnetic mats   */
    p->ramp_cycles  = 5;
    p->hold_cycles  = 5;
    p->degauss      = true;
}

void sweep_gen_cycle(const sweep_params_t *p, float amp,
                     float *out, int n)
{
    if (!p || !out || n <= 0) return;
    float peak = amp * p->i_peak;
    for (int i = 0; i < n; i++) {
        float t = (float)i / (float)n;        /* 0..1 of one cycle */
        float phase = t * 2.0f * (float)M_PI;
        switch (p->waveform) {
        case SWEEP_SIN:
            out[i] = peak * sinf(phase);
            break;
        case SWEEP_TRI:
            out[i] = (t < 0.5f)
                ? peak * (4.0f * t - 1.0f)
                : peak * (3.0f - 4.0f * t);
            break;
        case SWEEP_DC:
            /* quasi-DC: slow ramp up then down over the cycle */
            out[i] = (t < 0.5f)
                ? peak * (2.0f * t)
                : peak * (2.0f - 2.0f * t);
            break;
        default:
            out[i] = 0.0f;
            break;
        }
    }
}

void sweep_gen_degauss(float *amps, int n_cycles)
{
    /* Exponential decay from 1.0 to ~0 over n_cycles. */
    for (int i = 0; i < n_cycles; i++) {
        float t = (float)i / (float)n_cycles;
        amps[i] = expf(-4.0f * t);   /* e^-4 ≈ 0.018 at the end */
    }
}