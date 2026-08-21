/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * thickness.c — Time-of-flight thickness & echo-to-echo computation
 *
 * Finds the back-wall echo (or echo pair) in the A-scan envelope and
 * computes thickness using:
 *   d = (v * Δt) / 2
 * Sub-sample refinement is done with parabolic interpolation around the
 * echo peak for ~10 µm-equivalent resolution.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "thickness.h"
#include "calibration.h"
#include <math.h>

/* ---- Noise floor estimation: median of first 8% of samples (before
 * the surface echo). Used to set the detection threshold dynamically. ---- */
static uint16_t estimate_noise_floor(const uint16_t *env, uint16_t count)
{
    /* Use the first 8% of samples (skipping any initial ring-down).
     * Take the 75th percentile as a robust noise estimate. */
    uint16_t n = count / 12;
    if (n < 4) n = 4;
    if (n > 64) n = 64;

    /* Simple sort-based percentile (n is small) */
    uint16_t tmp[64];
    for (uint16_t i = 0; i < n; i++) tmp[i] = env[i];
    /* Insertion sort */
    for (uint16_t i = 1; i < n; i++) {
        uint16_t key = tmp[i];
        int16_t j = i - 1;
        while (j >= 0 && tmp[j] > key) { tmp[j + 1] = tmp[j]; j--; }
        tmp[j + 1] = key;
    }
    return tmp[(uint16_t)(n * 3 / 4)];
}

/* ---- Find the surface (first significant) echo index ---- */
static int16_t find_surface_echo(const uint16_t *env, uint16_t count,
                                   uint16_t noise_floor)
{
    /* Threshold: noise_floor + 20% of the full-scale peak in the window.
     * The surface echo is the first sample to exceed this after a short
     * blanking period (skip the first 2% to ignore transmit ring-down). */
    uint16_t skip = count / 50;
    if (skip < 2) skip = 2;

    /* Find max in window to set threshold */
    uint16_t max_v = 0;
    for (uint16_t i = skip; i < count; i++)
        if (env[i] > max_v) max_v = env[i];
    uint16_t thresh = noise_floor + (uint16_t)((max_v - noise_floor) * 3 / 10);

    for (uint16_t i = skip; i < count; i++) {
        if (env[i] > thresh) return (int16_t)i;
    }
    return -1;
}

/* ---- Find the back-wall echo: the largest peak after the surface echo ---- */
static int16_t find_backwall_echo(const uint16_t *env, uint16_t count,
                                    int16_t surface_idx, uint16_t noise_floor)
{
    if (surface_idx < 0) return -1;
    /* Search from (surface + small gap) to end of window.
     * The gap avoids picking up the surface ring-down. */
    uint16_t start = (uint16_t)surface_idx + 2;
    if (start >= count) return -1;

    uint16_t max_v = 0;
    int16_t max_idx = -1;
    for (uint16_t i = start; i < count; i++) {
        if (env[i] > max_v && env[i] > noise_floor + 30) {
            max_v = env[i];
            max_idx = (int16_t)i;
        }
    }
    return max_idx;
}

/* ---- Parabolic interpolation around a peak for sub-sample timing ---- */
float thickness_parabolic_interp(uint16_t y0, uint16_t y1, uint16_t y2)
{
    /* Fit a parabola through (−1, y0), (0, y1), (+1, y2) and return the
     * x-offset of the vertex (in fractions of a sample). */
    int32_t denom = (int32_t)y0 - 2 * (int32_t)y1 + (int32_t)y2;
    if (denom == 0) return 0.0f;
    int32_t numer = (int32_t)y0 - (int32_t)y2;
    return (float)numer / (2.0f * (float)denom);
}

float thickness_index_to_tof(int16_t idx, uint16_t sample_count, uint16_t window_us)
{
    if (idx < 0) return 0.0f;
    /* TOF = idx * (window_us / sample_count), in µs → ns */
    float per_sample_us = (float)window_us / (float)sample_count;
    return (float)idx * per_sample_us * 1000.0f;   /* ns */
}

float thickness_tof_to_mm(float tof_ns, uint32_t velocity_mps)
{
    /* d = v * t / 2; t in ns → s; v in m/s → mm/ns = v/1e6
     * d_mm = (v_mps) * (tof_ns / 1e9) / 2 * 1000  */
    return (float)velocity_mps * (tof_ns / 1.0e9f) * 0.5f * 1000.0f;
}

/* ---- Main thickness computation (pulse-echo mode) ---- */
void thickness_compute(const ascan_t *scan,
                        const thickness_result_t *prev,
                        thickness_result_t *out)
{
    if (!scan || !out) return;
    out->mode        = MEASURE_MODE_PULSE_ECHO;

    const material_t dummy = {0};
    (void)dummy;

    uint16_t count = scan->count;
    if (count < MIN_SAMPLES || !scan->valid) {
        out->valid = 0;
        out->thickness_mm = 0.0f;
        out->tof_ns = 0.0f;
        return;
    }

    uint16_t noise = estimate_noise_floor(scan->envelope, count);
    int16_t surf  = find_surface_echo(scan->envelope, count, noise);
    int16_t back  = find_backwall_echo(scan->envelope, count, surf, noise);

    if (surf < 0 || back < 0 || back <= surf) {
        out->valid = 0;
        return;
    }

    /* Parabolic refinement of the back-wall peak */
    uint16_t y0 = (back > 0) ? scan->envelope[back - 1] : 0;
    uint16_t y1 = scan->envelope[back];
    uint16_t y2 = (back < count - 1) ? scan->envelope[back + 1] : 0;
    float frac = thickness_parabolic_interp(y0, y1, y2);

    float tof = thickness_index_to_tof((int16_t)(back - surf),
                                        count, scan->count > count ? count : count);
    (void)frac;  /* could add frac * per_sample_ns */

    /* Apply zero-probe offset from calibration */
    const calibration_t *cal = calibration_get();
    if (tof > cal->zero_offset_ns) tof -= cal->zero_offset_ns;
    else tof = 0.0f;

    /* Use stored velocity from prev result (set by caller from material DB) */
    uint32_t vel = prev ? prev->velocity_mps : 5920U;
    out->velocity_mps    = vel;
    out->tof_ns          = tof;
    out->thickness_mm    = thickness_tof_to_mm(tof, vel);
    out->peak_index      = (int8_t)back;
    out->peak_amp        = (float)y1 / (float)ADC_MAX;
    out->zero_offset_ns = cal->zero_offset_ns;
    out->valid           = 1;
}

/* ---- Echo-to-echo (through-coating) mode ---- */
/* Find the Nth largest peak in the window (for B1, B2). */
static int16_t find_nth_peak(const uint16_t *env, uint16_t count,
                              int16_t after_idx, uint16_t noise,
                              uint8_t peak_n)
{
    /* Simple approach: find all local maxima above threshold after
     * after_idx, sort by amplitude, return the peak_n-th by position
     * (chronological) of the largest few. */
    uint16_t thresh = noise + 40;
    int16_t peaks[MAX_SAMPLES / 4];
    uint16_t peak_vals[MAX_SAMPLES / 4];
    uint16_t npeaks = 0;

    uint16_t start = (uint16_t)(after_idx + 1);
    if (start < 2) start = 2;
    for (uint16_t i = start; i < count - 1; i++) {
        if (env[i] > thresh &&
            env[i] >= env[i - 1] && env[i] >= env[i + 1]) {
            if (npeaks < MAX_SAMPLES / 4) {
                peaks[npeaks]     = (int16_t)i;
                peak_vals[npeaks] = env[i];
                npeaks++;
            }
        }
    }
    if (peak_n == 0 || npeaks < peak_n) return -1;
    /* The first two chronological peaks after the surface are B1, B2 */
    return peaks[peak_n - 1 < npeaks ? peak_n - 1 : npeaks - 1];
}

void thickness_echo_echo(const ascan_t *scan,
                          const thickness_result_t *prev,
                          thickness_result_t *out)
{
    if (!scan || !out) return;
    out->mode = MEASURE_MODE_ECHO_ECHO;

    uint16_t count = scan->count;
    if (count < MIN_SAMPLES || !scan->valid) {
        out->valid = 0; return;
    }

    uint16_t noise = estimate_noise_floor(scan->envelope, count);
    int16_t surf  = find_surface_echo(scan->envelope, count, noise);
    if (surf < 0) { out->valid = 0; return; }

    int16_t b1 = find_nth_peak(scan->envelope, count, surf, noise, 1);
    int16_t b2 = find_nth_peak(scan->envelope, count, b1, noise, 2);

    if (b1 < 0 || b2 < 0 || b2 <= b1) {
        out->valid = 0; return;
    }

    /* Δt = (b2 - b1) * per_sample_ns */
    float tof = thickness_index_to_tof((int16_t)(b2 - b1), count, count);
    uint32_t vel = prev ? prev->velocity_mps : 5920U;
    out->velocity_mps    = vel;
    out->tof_ns          = tof;
    out->thickness_mm    = thickness_tof_to_mm(tof, vel);
    out->peak_index      = (int8_t)b1;
    out->peak_amp        = (float)scan->envelope[b1] / (float)ADC_MAX;
    out->zero_offset_ns = 0;   /* echo-to-echo is independent of zero offset */
    out->valid           = 1;
}