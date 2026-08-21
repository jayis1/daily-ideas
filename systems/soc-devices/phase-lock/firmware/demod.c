/*
 * demod.c — I/Q digital demodulation + IIR low-pass filter
 *
 * Pipeline (runs at f_s = 28 ksps):
 *   1. Pull latest oversampled ADC sample s[n] (16-bit, 0..65535).
 *   2. Convert to volts (0 V at mid-scale 32768; ±10 V full-scale at 1× gain).
 *   3. Pull I/Q reference (q1.31) from ref_osc.
 *   4. Mix: I_raw = s × i_ref / 2^31 ; Q_raw = s × q_ref / 2^31.
 *   5. Apply cascaded 2nd-order IIR low-pass (CMSIS-DSP biquad) with the
 *      selected time constant and slope.
 *   6. Compute R = √(I² + Q²), θ = atan2(Q, I).
 *   7. Compute noise floor from the residual AC component in I/Q.
 *
 * The biquad coefficients for each time constant are precomputed for
 * f_s = 28 ksps, 2nd-order Butterworth, with the cutoff = 1/(2π·TC).
 */

#include "stm32g491_conf.h"
#include "demod.h"
#include "adc.h"
#include "ref_osc.h"
#include "pga.h"
#include <math.h>

const float tc_table[TC_COUNT] = {
    0.0005f, 0.001f, 0.003f, 0.01f, 0.03f, 0.1f, 0.3f, 1.0f, 3.0f, 10.0f
};

#define FS        28000.0f
#define PI        3.14159265358979f
#define MAX_STAGES 8

typedef struct {
    float b0, b1, b2, a1, a2;
    float x1, x2, y1, y2;
} biquad_t;

static biquad_t   iir_I[MAX_STAGES];
static biquad_t   iir_Q[MAX_STAGES];
static int        n_stages = 1;
static time_const_t cur_tc = TC_10MS;
static slope_t    cur_slope = SLOPE_6;
static float      I_filt, Q_filt;
static float      noise_I, noise_Q;   /* running noise estimate */
static demod_result_t cur_result;

/* Compute Butterworth 2nd-order biquad coefficients for cutoff fc at fs */
static void biquad_lp(biquad_t *bq, float fc, float fs)
{
    float k = tanf(PI * fc / fs);
    float k2 = k * k;
    float norm = 1.0f + (sqrtf(2.0f) * k) + k2;
    bq->b0 = k2 / norm;
    bq->b1 = 2.0f * bq->b0;
    bq->b2 = bq->b0;
    bq->a1 = 2.0f * (k2 - 1.0f) / norm;
    bq->a2 = (sqrtf(2.0f) * k - 1.0f - k2) / norm;
    bq->x1 = bq->x2 = bq->y1 = bq->y2 = 0.0f;
}

static inline float biquad_run(biquad_t *bq, float x)
{
    float y = bq->b0 * x + bq->b1 * bq->x1 + bq->b2 * bq->x2
              - bq->a1 * bq->y1 - bq->a2 * bq->y2;
    bq->x2 = bq->x1;  bq->x1 = x;
    bq->y2 = bq->y1;  bq->y1 = y;
    return y;
}

void demod_init(void)
{
    cur_tc = TC_10MS;
    cur_slope = SLOPE_6;
    demod_reset();
    demod_set_tc(cur_tc);
    demod_set_slope(cur_slope);
}

void demod_reset(void)
{
    I_filt = Q_filt = 0.0f;
    noise_I = noise_Q = 0.0f;
    for (int i = 0; i < MAX_STAGES; ++i) {
        iir_I[i].x1 = iir_I[i].x2 = iir_I[i].y1 = iir_I[i].y2 = 0.0f;
        iir_Q[i].x1 = iir_Q[i].x2 = iir_Q[i].y1 = iir_Q[i].y2 = 0.0f;
    }
}

void demod_set_tc(time_const_t tc)
{
    cur_tc = tc;
    float fc = 1.0f / (2.0f * PI * tc_table[tc]);
    for (int i = 0; i < n_stages; ++i)
        biquad_lp(&iir_I[i], fc, FS);
    for (int i = 0; i < n_stages; ++i)
        biquad_lp(&iir_Q[i], fc, FS);
}

void demod_set_slope(slope_t s)
{
    cur_slope = s;
    switch (s) {
        case SLOPE_6:  n_stages = 1; break;
        case SLOPE_12: n_stages = 2; break;
        case SLOPE_24: n_stages = 4; break;
        case SLOPE_48: n_stages = 8; break;
    }
    demod_set_tc(cur_tc);  /* recompute coefficients */
}

void demod_process(void)
{
    int32_t s = adc_get_sample();              /* 16-bit, 0..65535 */
    /* Convert to volts: mid-scale 32768 = 0 V; ±32768 = ±10 V / gain */
    float gain = pga_get_gain();
    float sv = ((float)s - 32768.0f) / 32768.0f * 10.0f / gain;

    int32_t i_ref, q_ref;
    ref_osc_get_iq(&i_ref, &q_ref);
    float ir = (float)i_ref / 2147483648.0f;
    float qr = (float)q_ref / 2147483648.0f;

    float I_raw = sv * ir;
    float Q_raw = sv * qr;

    /* Cascade IIR low-pass on I and Q */
    float I = I_raw, Q = Q_raw;
    for (int i = 0; i < n_stages; ++i) {
        I = biquad_run(&iir_I[i], I);
        Q = biquad_run(&iir_Q[i], Q);
    }
    I_filt = I;
    Q_filt = Q;

    /* R, θ */
    cur_result.R = sqrtf(I * I + Q * Q) * 2.0f;   /* ×2 for single-sideband */
    cur_result.theta = atan2f(Q, I);
    cur_result.X = I;
    cur_result.Y = Q;

    /* Noise floor: high-pass I/Q at ~10/TC and take RMS */
    float hp = I_raw - I_filt;   /* residual AC component (single-stage approx) */
    noise_I = 0.99f * noise_I + 0.01f * hp * hp;
    float bw = 1.0f / (4.0f * tc_table[cur_tc]);  /* ENBW (Hz) for 1 stage */
    cur_result.noise = sqrtf(noise_I) / sqrtf(bw);
}

demod_result_t demod_read(void)
{
    return cur_result;
}