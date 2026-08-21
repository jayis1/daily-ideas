/*
 * sweep.c — frequency and amplitude sweep engine
 *
 * Drives a frequency or amplitude sweep by stepping the reference
 * oscillator through N points (log or linear) and recording R/θ/X/Y
 * at each point. The sweep is controlled by the main state machine.
 *
 * The settle time per point is 3·TC (3 time constants), to let the
 * IIR LPF reach ~95% of the final value. The sweep is logged to SD
 * as a CSV table and streamed over BLE per-point.
 */

#include "stm32g491_conf.h"
#include "sweep.h"
#include "ref_osc.h"
#include "demod.h"
#include <math.h>

sweep_state_t g_sweep;
static sweep_point_t last_point;

void sweep_init(void)
{
    g_sweep.mode = SWEEP_NONE;
    g_sweep.running = false;
}

static float logf10f(float x) { return logf(x) / logf(10.0f); }

void sweep_start_freq(float f1, float f2, uint16_t n, bool logspace)
{
    g_sweep.mode = SWEEP_FREQ;
    g_sweep.f_start = f1;
    g_sweep.f_stop  = f2;
    g_sweep.n_points = n;
    g_sweep.log_spacing = logspace;
    g_sweep.cur_point = 0;
    g_sweep.running = true;
    /* Set first point */
    ref_osc_set_freq(f1);
    ref_osc_start();
}

void sweep_start_amp(float a1, float a2, uint16_t n)
{
    g_sweep.mode = SWEEP_AMP;
    g_sweep.a_start = a1;
    g_sweep.a_stop  = a2;
    g_sweep.n_points = n;
    g_sweep.log_spacing = false;
    g_sweep.cur_point = 0;
    g_sweep.running = true;
    ref_osc_set_amplitude(a1);
    ref_osc_start();
}

void sweep_stop(void)
{
    g_sweep.running = false;
    g_sweep.mode = SWEEP_NONE;
    ref_osc_stop();
}

bool sweep_running(void) { return g_sweep.running; }
uint16_t sweep_point(void) { return g_sweep.cur_point; }
uint16_t sweep_npoints(void) { return g_sweep.n_points; }

float sweep_current_freq(void)
{
    if (g_sweep.mode == SWEEP_FREQ) {
        if (g_sweep.log_spacing) {
            float l1 = logf10f(g_sweep.f_start);
            float l2 = logf10f(g_sweep.f_stop);
            float t = (float)g_sweep.cur_point / (float)(g_sweep.n_points - 1);
            return powf(10.0f, l1 + t * (l2 - l1));
        } else {
            float t = (float)g_sweep.cur_point / (float)(g_sweep.n_points - 1);
            return g_sweep.f_start + t * (g_sweep.f_stop - g_sweep.f_start);
        }
    }
    return 0.0f;
}

float sweep_current_amp(void)
{
    if (g_sweep.mode == SWEEP_AMP) {
        float t = (float)g_sweep.cur_point / (float)(g_sweep.n_points - 1);
        return g_sweep.a_start + t * (g_sweep.a_stop - g_sweep.a_start);
    }
    return 0.0f;
}

bool sweep_step(void)
{
    if (!g_sweep.running) return false;
    if (g_sweep.cur_point >= g_sweep.n_points) {
        sweep_stop();
        return false;
    }
    /* Set the frequency/amplitude for the current point */
    if (g_sweep.mode == SWEEP_FREQ) {
        ref_osc_set_freq(sweep_current_freq());
    } else if (g_sweep.mode == SWEEP_AMP) {
        ref_osc_set_amplitude(sweep_current_amp());
    }
    /* Wait 3·TC for settle (called from main loop, non-blocking in real impl) */
    /* The main state machine handles the dwell; here we just record the point */
    demod_result_t r = demod_read();
    last_point.f     = sweep_current_freq();
    last_point.a     = sweep_current_amp();
    last_point.R     = r.R;
    last_point.theta = r.theta;
    last_point.X     = r.X;
    last_point.Y     = r.Y;
    last_point.noise = r.noise;
    last_point.ts_ms = 0;   /* filled in by caller with SysTick */
    g_sweep.cur_point++;
    return true;
}

sweep_point_t sweep_last_point(void) { return last_point; }