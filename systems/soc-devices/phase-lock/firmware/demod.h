/*
 * demod.h — I/Q digital demodulation + IIR low-pass filter
 */
#ifndef DEMOD_H
#define DEMOD_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    TC_0_5MS = 0, TC_1MS, TC_3MS, TC_10MS, TC_30MS, TC_100MS,
    TC_300MS, TC_1S, TC_3S, TC_10S, TC_COUNT
} time_const_t;

typedef enum {
    SLOPE_6  = 0,   /*  6 dB/oct — 1 stage */
    SLOPE_12 = 1,   /* 12 dB/oct — 2 stages */
    SLOPE_24 = 2,   /* 24 dB/oct — 4 stages */
    SLOPE_48 = 3,   /* 48 dB/oct — 8 stages */
} slope_t;

typedef struct {
    float R;       /* magnitude (V)  */
    float theta;   /* phase (rad)    */
    float X;       /* in-phase     = R·cosθ  (V) */
    float Y;       /* quadrature   = R·sinθ  (V) */
    float noise;  /* noise floor at f0 (V/√Hz) */
} demod_result_t;

void demod_init(void);
void demod_set_tc(time_const_t tc);
void demod_set_slope(slope_t s);
void demod_reset(void);

/* Process one ADC sample → update internal state.
 * Called from main loop at f_s = 28 ksps; pulls the latest ADC sample
 * and the current I/Q reference, mixes, and applies the IIR LPF.
 */
void demod_process(void);

/* Read the latest filtered R/θ/X/Y/noise. Safe to call from main thread. */
demod_result_t demod_read(void);

extern const float tc_table[TC_COUNT];   /* seconds */

#endif /* DEMOD_H */