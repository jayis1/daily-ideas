/*
 * port_sim.c — host simulation shim
 *
 * Stubs the STM32 HAL / hardware so the B-H math path (sweep.c, bh.c,
 * adc.c engineering conversion, sdlog.c) can be exercised on a host
 * without any hardware. The sim feeds bh.c a synthetic hysteresis model:
 *
 *   B(H) = B_sat * tanh((H ± H_c) / H_k)
 *
 * with a sign chosen so the loop has the right handedness, producing a
 * realistic-looking hysteresis loop. The sim then prints the computed
 * B_sat, H_c, B_r, mu_dc, P_v and writes a CSV/JSON to the CWD so the
 * Python plotter can read it back.
 */
#include "sweep.h"
#include "adc.h"
#include "bh.h"
#include "power.h"
#include "display.h"
#include "sdlog.h"
#include "esp_link.h"

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* ── Stubbed HAL functions referenced by the real modules ─────────────── */
/* adc.c already provides adc_dma_tc_callback(); no override needed. */

/* The real adc.c provides these, but we override the engineering
 * conversion to feed a synthetic B(H) model instead of raw ADC counts. */

/* ── Synthetic specimen model ─────────────────────────────────────────── */
/* Simulated 3E25-like soft ferrite:
 *   B_sat ≈ 0.40 T, H_c ≈ 20 A/m, H_k = 30 A/m (knee sharpness) */
static double sim_b_sat = 0.40;
static double sim_h_c   = 20.0;
static double sim_h_k   = 30.0;

/* Generate a synthetic H sweep + B(H) hysteresis loop covering one full
 * cycle at the peak amplitude. n samples, H peaks at h_peak (A/m). */
static void sim_gen_loop(float *H, float *B, int n, float h_peak,
                         float freq, sweep_waveform_t wf)
{
    (void)freq;
    for (int i = 0; i < n; i++) {
        double t = (double)i / n;        /* 0..1 over one cycle */
        double phase = t * 2.0 * M_PI;
        double h;
        switch (wf) {
        case SWEEP_TRI:
            h = (t < 0.5) ? h_peak * (4*t - 1) : h_peak * (3 - 4*t);
            break;
        case SWEEP_DC:
            h = (t < 0.5) ? h_peak * (2*t) : h_peak * (2 - 2*t);
            break;
        default:
            h = h_peak * sin(phase);
            break;
        }
        H[i] = (float)h;
        /* Hysteresis branch: upper branch for increasing H, lower for
         * decreasing. We pick the sign of dH/dt. */
        double dhdt = cos(phase);   /* works for sin; for tri use slope */
        if (wf == SWEEP_TRI) dhdt = (t < 0.5) ? +1 : -1;
        if (wf == SWEEP_DC)  dhdt = (t < 0.5) ? +1 : -1;
        double sign = (dhdt > 0) ? +1.0 : -1.0;
        double b = sim_b_sat * tanh((h - sign * sim_h_c) / sim_h_k);
        B[i] = (float)b;
    }
}

/* ── Sim main ─────────────────────────────────────────────────────────── */
int main(void)
{
    printf("Ferro Weave — host simulation\n");
    printf("==============================\n");

    geom_t g = {
        .n1 = 100, .n2 = 100,
        .l_e = 0.0785f,
        .a2 = 31.4e-6f,
        .a_core = 31.4e-6f,
        .rho = 4800.0f,
        .freq = 10.0f,
    };

    sweep_params_t sp;
    sweep_defaults(&sp);
    sp.waveform = SWEEP_SIN;
    sp.i_peak   = 1.0f;
    sp.freq     = 10.0f;

    /* H_peak from I_peak: H = N1·I/l_e */
    float h_peak = (float)g.n1 * sp.i_peak / g.l_e;   /* ~1274 A/m */

    const int n = 1024;
    static float H[1024], B[1024];
    sim_gen_loop(H, B, n, h_peak, sp.freq, sp.waveform);

    /* Air-flux correction is a no-op here (a2 == a_core). */
    bh_result_t r;
    if (bh_compute(H, B, n, &g, &r) != 0) {
        fprintf(stderr, "bh_compute failed\n");
        return 1;
    }

    printf("\nSynthetic specimen: B_sat=%.2f T, H_c=%.1f A/m, H_k=%.1f A/m\n",
           sim_b_sat, sim_h_c, sim_h_k);
    printf("Sweep: %s, I_peak=%.2f A, H_peak=%.1f A/m, f=%.1f Hz, N=%d\n",
           sp.waveform == SWEEP_SIN ? "SIN" :
           sp.waveform == SWEEP_TRI ? "TRI" : "DC",
           sp.i_peak, h_peak, sp.freq, n);
    printf("\n── Computed B-H loop result ──\n");
    printf("  B_sat        = %.4f T        (expected ~%.2f)\n", r.b_sat, sim_b_sat);
    printf("  H_c          = %.2f A/m      (expected ~%.1f)\n", r.h_c, sim_h_c);
    printf("  B_r          = %.4f T\n", r.b_r);
    printf("  mu_dc        = %.1f\n", r.mu_dc);
    printf("  mu_inc_peak  = %.1f\n", r.mu_inc_peak);
    printf("  P_v          = %.4f W/kg\n", r.p_v);
    printf("  squareness   = %.3f\n", r.squareness);
    printf("  loop_area    = %.6f T·A/m  (J/m³)\n", r.loop_area);
    printf("  n_points     = %d\n", r.n_points);

    /* Write a CSV + JSON to the CWD for the Python plotter. */
    sdlog_write(&sp, &g, H, B, n, &r);
    printf("\nWrote BH_*.csv and BH_*.json to the CWD.\n");
    printf("Plot with: python3 ../../scripts/bh_plotter.py --batch BH_*.csv\n");
    return 0;
}