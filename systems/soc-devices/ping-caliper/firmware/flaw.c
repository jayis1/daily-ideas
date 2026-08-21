/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * flaw.c — Gate-based flaw detection and DGS equivalent sizing
 *
 * A movable gate (in time/depth) is placed between the surface and
 * back-wall echoes. Any peak inside the gate above a threshold is flagged
 * as a flaw. The equivalent reflector size is estimated with a simplified
 * DGS (distance–gain–size) model based on the probe's near-field length.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "flaw.h"
#include "thickness.h"
#include <math.h>

static flaw_gate_t g_gate;

void flaw_init(void)
{
    g_gate.start_us  = 5;
    g_gate.width_us  = 80;
    g_gate.threshold = 200;
    g_gate.enabled   = 0;
}

void flaw_set_gate(const flaw_gate_t *gate)
{
    g_gate = *gate;
    if (g_gate.width_us == 0) g_gate.width_us = 1;
}

void flaw_get_gate(flaw_gate_t *gate) { *gate = g_gate; }

/* Convert gate time (µs) → sample index. */
static int16_t gate_us_to_idx(uint16_t us, uint16_t count, uint16_t window_us)
{
    float frac = (float)us / (float)window_us;
    int16_t idx = (int16_t)(frac * (float)count);
    if (idx < 0) idx = 0;
    if (idx >= (int16_t)count) idx = (int16_t)(count - 1);
    return idx;
}

void flaw_evaluate(const ascan_t *scan,
                    const thickness_result_t *thk,
                    flaw_result_t *out)
{
    if (!scan || !out) { if (out) out->detected = 0; return; }
    out->detected = 0;

    if (!g_gate.enabled || !scan->valid) return;

    uint16_t count = scan->count;
    int16_t gstart = gate_us_to_idx(g_gate.start_us, count, count);  /* approx window=count µs */
    int16_t gend   = gate_us_to_idx(g_gate.start_us + g_gate.width_us, count, count);
    if (gstart < 0) gstart = 0;
    if (gend >= (int16_t)count) gend = (int16_t)(count - 1);
    if (gend <= gstart) return;

    /* Find the maximum peak inside the gate */
    uint16_t max_v = 0;
    int16_t max_idx = -1;
    for (int16_t i = gstart; i <= gend; i++) {
        if (scan->envelope[i] > max_v) {
            max_v = scan->envelope[i];
            max_idx = i;
        }
    }

    if (max_idx < 0) return;

    /* Normalize amplitude (0..1) */
    float amp = (float)max_v / (float)ADC_MAX;

    /* Check threshold (also as a fraction) */
    float thr_frac = (float)g_gate.threshold / (float)ADC_MAX;
    if (amp < thr_frac) return;

    out->detected    = 1;
    out->peak_index  = max_idx;
    out->peak_amp    = amp;

    /* Depth from surface: use the material velocity */
    uint32_t vel = thk ? thk->velocity_mps : 5920U;
    /* Time from surface = (max_idx - surface_idx) * per_sample_ns.
     * We approximate surface_idx as 0 if thk->peak_index is for back-wall. */
    float per_sample_ns = (float)scan->window_us * 1000.0f / (float)count;
    float depth_ns = (float)max_idx * per_sample_ns;
    out->depth_mm  = thickness_tof_to_mm(depth_ns, vel);

    /* Equivalent reflector size (simplified DGS) */
    /* Assume 5 MHz, 6 mm element if not known (set by probe ID). */
    out->equiv_mm = flaw_dgs_equiv(out->depth_mm, amp, 5.0f, 6.0f);
}

/* ---- Simplified DGS (distance–gain–size) equivalent sizing ----
 *
 * The DGS diagram relates the echo amplitude from a disk-shaped reflector
 * to its equivalent flat-bottom-hole (FBH) diameter. We use a simplified
 * model:
 *
 *   N = a²/λ   (near-field length, a = element radius, λ = wavelength)
 *   A = 20 log10(amp / amp_ref)
 *   D_eq ≈ k * sqrt(depth / N) * 10^(A/40)
 *
 * where k is a probe-specific constant (here ~0.5 mm for a 6 mm element).
 */
float flaw_dgs_equiv(float depth_mm, float peak_amp, float freq_mhz, float elem_mm)
{
    if (depth_mm <= 0.0f || peak_amp <= 0.0f) return 0.0f;

    /* Wavelength in steel (v = 5920 m/s): λ = v/f */
    float v = 5920.0f;   /* m/s (default; could be parameterized) */
    float lambda_mm = v / (freq_mhz * 1.0e6f) * 1000.0f;   /* mm */

    /* Near-field length: N = a² / λ (a = element radius in mm) */
    float a_mm = elem_mm / 2.0f;
    float N_mm = (a_mm * a_mm) / lambda_mm;

    /* Normalized distance: gn = depth / N */
    float gn = depth_mm / N_mm;
    if (gn < 0.1f) gn = 0.1f;

    /* Equivalent FBH diameter (simplified):
     * D_eq ≈ elem_mm * sqrt(peak_amp / gn)  (empirical fit) */
    float d_eq = elem_mm * sqrtf(peak_amp / gn) * 0.3f;

    /* Clamp to reasonable range */
    if (d_eq < 0.1f) d_eq = 0.1f;
    if (d_eq > 10.0f) d_eq = 10.0f;
    return d_eq;
}