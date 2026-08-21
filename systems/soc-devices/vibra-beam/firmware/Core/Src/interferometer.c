/*
 * interferometer.c — quadrature homodyne LDV signal processing
 *
 * Pipeline: raw I/Q → baseline removal → CORDIC atan2 → phase unwrap →
 *           displacement (λ/4π × φ) → velocity (dφ/dt × λ/4π) →
 *           FMAC low-pass for velocity smoothing.
 *
 * The STM32G474 CORDIC computes atan2(y,x) in 7 cycles at full precision;
 * we use it for the per-sample phase extraction. Phase unwrapping handles
 * the 2π jumps; each 2π corresponds to λ/2 = 325 nm of target motion.
 */

#include "interferometer.h"
#include "stm32g4xx_hal.h"
#include <math.h>
#include <string.h>

/* CORDIC handle (STM32G474 hardware accelerator) */
extern CORDIC_HandleTypeDef hcordic;

static float s_lambda_nm = CONFIG_LAMBDA_NM;
static float s_frange_nm = CONFIG_FRANGE_NM;     /* 325 nm */
static float s_baseline_tau = 0.2f;              /* 200 ms baseline tracking */

/* ── Init ────────────────────────────────────────────────── */
void interferometer_init(void)
{
    s_lambda_nm = CONFIG_LAMBDA_NM;
    s_frange_nm = CONFIG_LAMBDA_NM / 2.0f;
    s_baseline_tau = CONFIG_BASELINE_TAU_MS / 1000.0f;

    /* Configure CORDIC for atan2 (qsize=32, qlen=24) */
    if (&hcordic != NULL && hcordic.Instance != NULL) {
        hcordic.Instance = CORDIC;
        LL_CORDIC_SetFunction(hcordic.Instance, LL_CORDIC_FUNC_ATAN2);
        LL_CORDIC_SetPrecision(hcordic.Instance, LL_CORDIC_PRECISION_24ITER);
        LL_CORDIC_SetScale(hcordic.Instance, LL_CORDIC_SCALE_0);
        __HAL_RCC_CORDIC_CLK_ENABLE();
    }
}

void interferometer_reset(void)
{
    /* Reset phase tracker — caller fills g_phase fresh */
}

/* ── CORDIC atan2 wrapper ────────────────────────────────── */
float cordic_atan2f(float y, float x)
{
    /* If CORDIC present, use it; else fall back to libc atan2f */
    if (&hcordic != NULL && hcordic.Instance != NULL) {
        int32_t q[2];
        /* Convert to Q1.31 fixed-point */
        q[0] = (int32_t)(y * 2147483647.0f);
        q[1] = (int32_t)(x * 2147483647.0f);
        int32_t r;
        HAL_CORDIC_Calculate(&hcordic, q, &r, 2, 1);
        /* Result is in radians scaled by π; convert back */
        return (float)r * (3.14159265358979323846f / 2147483647.0f);
    }
    return atan2f(y, x);
}

/* ── Baseline tracking ───────────────────────────────────── */
void interferometer_update_baseline(const iq_block_t *iq)
{
    /* DC estimate = block mean; leaky integrator for slow tracking */
    float mean_i = 0.0f, mean_q = 0.0f;
    for (uint32_t i = 0; i < iq->n; i++) {
        mean_i += iq->i[i];
        mean_q += iq->q[i];
    }
    mean_i /= iq->n;
    mean_q /= iq->n;

    /* First-time initialization */
    static uint8_t first = 1;
    static float bi = 0.0f, bq = 0.0f;
    if (first) {
        bi = mean_i; bq = mean_q; first = 0;
    } else {
        float alpha = 0.05f;  /* IIR smoothing */
        bi = bi * (1.0f - alpha) + mean_i * alpha;
        bq = bq * (1.0f - alpha) + mean_q * alpha;
    }
    /* Stash into the phase block we'll use next */
    /* (Phase block baseline is stored per-instance in caller) */
}

/* ── Main processing: I/Q → phase → disp → vel ──────────── */
void interferometer_process(const iq_block_t *iq, phase_block_t *pb)
{
    /* Compute baseline (DC offset) from block means */
    float mean_i = 0.0f, mean_q = 0.0f;
    for (uint32_t i = 0; i < iq->n; i++) {
        mean_i += iq->i[i];
        mean_q += iq->q[i];
    }
    mean_i /= iq->n;
    mean_q /= iq->n;

    /* Amplitude estimate (radius of I/Q circle) */
    float radius = 0.0f;
    for (uint32_t i = 0; i < iq->n; i++) {
        float di = iq->i[i] - mean_i;
        float dq = iq->q[i] - mean_q;
        radius += sqrtf(di * di + dq * dq);
    }
    radius /= iq->n;
    if (radius < 1.0f) radius = 1.0f;   /* avoid div-by-zero */

    /* Phase extraction with unwrapping */
    float prev_phase = pb->last_phase;
    float unwrap_accum = 0.0f;
    for (uint32_t i = 0; i < iq->n; i++) {
        float di = (iq->i[i] - mean_i) / radius;
        float dq = (iq->q[i] - mean_q) / radius;
        float phi = cordic_atan2f(dq, di);   /* −π..π */

        /* Unwrap: detect jumps > π */
        float delta = phi - prev_phase;
        if (delta > M_PI)  unwrap_accum -= 2.0f * M_PI;
        else if (delta < -M_PI) unwrap_accum += 2.0f * M_PI;
        prev_phase = phi;

        float phi_unwrapped = phi + unwrap_accum;
        pb->phase_rad[i] = phi_unwrapped;

        /* Displacement: x = (λ/4π) × φ */
        pb->disp_nm[i] = (s_lambda_nm / (4.0f * (float)M_PI)) * phi_unwrapped;
    }
    pb->last_phase = prev_phase;
    pb->baseline_i = mean_i;
    pb->baseline_q = mean_q;

    /* Velocity = dφ/dt × λ/4π
     * Sample interval dt = 1 / sample_rate.
     * Use first-difference + simple one-pole IIR low-pass.
     */
    const float dt = 1.0f / (float)CONFIG_ADC_SAMPLE_RATE_HZ;
    const float fc = CONFIG_VEL_LP_FC_DEFAULT_HZ;
    float alpha = 1.0f - expf(-2.0f * (float)M_PI * fc * dt);
    if (alpha > 1.0f) alpha = 1.0f;
    if (alpha < 0.0f) alpha = 0.0f;

    float vel_prev = 0.0f;
    for (uint32_t i = 0; i < iq->n; i++) {
        if (i == 0) {
            float dphi = pb->phase_rad[0] - pb->last_phase;
            pb->vel_mms[0] = (dphi / dt) * (s_lambda_nm / (4.0f * (float)M_PI)) * 1e-6f; /* nm/s → mm/s */
        } else {
            float dphi = pb->phase_rad[i] - pb->phase_rad[i - 1];
            float v_raw = (dphi / dt) * (s_lambda_nm / (4.0f * (float)M_PI)) * 1e-6f;
            /* one-pole low-pass */
            vel_prev = vel_prev * (1.0f - alpha) + v_raw * alpha;
            pb->vel_mms[i] = vel_prev;
        }
    }
    pb->n = iq->n;
}