/*
 * pyro-balance / Core/Src/tga.c
 * TG/DTG computation, step detection, Kissinger/Ozawa kinetics.
 */
#include "tga.h"
#include <math.h>

tga_run_t g_run;

void tga_reset(float m0_mg) {
    memset(&g_run, 0, sizeof(g_run));
    g_run.m0_mg = m0_mg;
}

void tga_push(float temp_c, float mass_mg, uint32_t t_ms) {
    if (g_run.n >= TGA_MAX_SAMPLES) return;
    uint32_t i = g_run.n;
    g_run.temp_c[i] = temp_c;
    g_run.mass_pct[i] = (g_run.m0_mg > 0) ? (mass_mg / g_run.m0_mg) * 100.0f : 100.0f;
    g_run.n++;
}

/* Savitzky-Golay-ish 5-point smoothing */
static float sg5(const float* y, int i, int n) {
    if (i < 2 || i > n-3) return y[i];
    return (-3*y[i-2] + 12*y[i-1] + 17*y[i] + 12*y[i+1] - 3*y[i+2]) / 35.0f;
}

void tga_finalize(void) {
    int n = g_run.n;
    if (n < 5) return;

    /* smoothed mass → DTG (per minute, using 1 Hz spacing → dt = 1/60 min) */
    for (int i = 1; i < n-1; i++) {
        float m_prev = sg5(g_run.mass_pct, i-1, n);
        float m_next = sg5(g_run.mass_pct, i+1, n);
        /* central difference, dt = 2 s = 2/60 min */
        g_run.dtg_pct_per_min[i] = (m_next - m_prev) / (2.0f / 60.0f);
    }
    g_run.dtg_pct_per_min[0] = 0;
    g_run.dtg_pct_per_min[n-1] = 0;

    /* peak detection on |DTG| */
    float dtg_mean = 0, dtg_std = 0;
    for (int i = 0; i < n; i++) dtg_mean += fabsf(g_run.dtg_pct_per_min[i]);
    dtg_mean /= n;
    for (int i = 0; i < n; i++) {
        float d = fabsf(g_run.dtg_pct_per_min[i]) - dtg_mean;
        dtg_std += d*d;
    }
    dtg_std = sqrtf(dtg_std / n);

    float thresh = dtg_mean + 4.0f * dtg_std;
    int step = 0;
    int refractory_end = 0;
    for (int i = 10; i < n-10 && step < TGA_MAX_STEPS; i++) {
        if (i < refractory_end) continue;
        if (fabsf(g_run.dtg_pct_per_min[i]) > thresh) {
            /* find peak in window */
            int pk = i;
            float pkv = fabsf(g_run.dtg_pct_per_min[i]);
            int j = i+1;
            while (j < n-1 && fabsf(g_run.dtg_pct_per_min[j]) > thresh*0.3f) {
                if (fabsf(g_run.dtg_pct_per_min[j]) > pkv) {
                    pk = j; pkv = fabsf(g_run.dtg_pct_per_min[j]);
                }
                j++;
            }
            /* onset: extrapolate tangent at half-peak to zero DTG (simplified) */
            int onset_i = pk - 5;
            while (onset_i > 0 && fabsf(g_run.dtg_pct_per_min[onset_i]) > thresh*0.1f) onset_i--;
            int endset_i = j;
            while (endset_i < n-1 && fabsf(g_run.dtg_pct_per_min[endset_i]) > thresh*0.1f) endset_i++;

            float dmass = g_run.mass_pct[onset_i] - g_run.mass_pct[endset_i];
            if (dmass < 0) dmass = -dmass;
            g_run.steps[step].valid = true;
            g_run.steps[step].onset_c = g_run.temp_c[onset_i];
            g_run.steps[step].peak_c  = g_run.temp_c[pk];
            g_run.steps[step].endset_c = g_run.temp_c[endset_i];
            g_run.steps[step].dmass_pct = dmass;
            g_run.steps[step].dtg_peak_pct_per_min = g_run.dtg_pct_per_min[pk];
            step++;
            refractory_end = endset_i + 30; /* 30 s refractory */
            i = endset_i;
        }
    }
    g_run.step_count = step;

    /* residual = mass at final temp */
    g_run.residual_pct = g_run.mass_pct[n-1];
}

const tga_run_t* tga_get(void) { return &g_run; }

/* Kissinger: ln(β/Tp²) = ln(AR/E) − E/(R·Tp) → slope = −E/R */
float tga_kissinger_E(const kissinger_pt_t* pts, uint8_t n) {
    if (n < 3) return 0;
    float Sx=0, Sy=0, Sxx=0, Sxy=0;
    for (int i = 0; i < n; i++) {
        float x = 1.0f / pts[i].tp_kelvin;
        float y = logf(pts[i].beta / (pts[i].tp_kelvin * pts[i].tp_kelvin));
        Sx += x; Sy += y; Sxx += x*x; Sxy += x*y;
    }
    float denom = n*Sxx - Sx*Sx;
    if (fabsf(denom) < 1e-12f) return 0;
    float slope = (n*Sxy - Sx*Sy) / denom;
    float R = 8.314f; /* J/(mol·K) */
    return -slope * R * 1000.0f; /* kJ/mol... but we want J/mol → ×1000 → kJ/mol. We return J/mol */
}

/* Ozawa–Flynn–Wall: ln(β) = const − 1.052*E/(R·Tp) → slope = −1.052*E/R */
float tga_ozawa_E(const kissinger_pt_t* pts, uint8_t n) {
    if (n < 3) return 0;
    float Sx=0, Sy=0, Sxx=0, Sxy=0;
    for (int i = 0; i < n; i++) {
        float x = 1.0f / pts[i].tp_kelvin;
        float y = logf(pts[i].beta);
        Sx += x; Sy += y; Sxx += x*x; Sxy += x*y;
    }
    float denom = n*Sxx - Sx*Sx;
    if (fabsf(denom) < 1e-12f) return 0;
    float slope = (n*Sxy - Sx*Sy) / denom;
    float R = 8.314f;
    return -slope * R / 1.052f; /* J/mol */
}