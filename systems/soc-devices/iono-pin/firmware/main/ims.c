/*
 * ims.c — Drift-tube ion mobility spectrometry DSP
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * Pipeline: baseline subtract -> 256-spectrum rolling average ->
 *           derivative peak detect -> K0 computation -> result.
 *
 * SPDX-License-Identifier: MIT
 */
#include "ims.h"
#include <string.h>
#include <math.h>

static ims_avg_t g_avg;

void ims_init(void)
{
    memset(&g_avg, 0, sizeof(g_avg));
}

void ims_reset_avg(void)
{
    g_avg.count = 0;
    memset(g_avg.acc, 0, sizeof(g_avg.acc));
}

void ims_accumulate(const int16_t *raw)
{
    if (g_avg.count >= IMS_AVG_COUNT) {
        /* Rolling: subtract oldest contribution by decaying accumulator.
         * Simpler approach: when full, subtract 1/256th of current acc
         * (exponential moving average approximation). */
        for (int i = 0; i < IMS_SAMPLES_PER_SWEEP; i++) {
            g_avg.acc[i] = (int32_t)((g_avg.acc[i] * (IMS_AVG_COUNT - 1)) / IMS_AVG_COUNT) + raw[i];
        }
    } else {
        for (int i = 0; i < IMS_SAMPLES_PER_SWEEP; i++) {
            g_avg.acc[i] += raw[i];
        }
        g_avg.count++;
    }
}

bool ims_result_ready(void)
{
    return g_avg.count >= 8;   /* usable after 8 sweeps */
}

/* Baseline: median of first 10 samples (pre-arrival region) */
static int16_t estimate_baseline(const int16_t *spec)
{
    int16_t b[10];
    memcpy(b, spec, sizeof(int16_t) * 10);
    /* simple insertion sort for 10 elements */
    for (int i = 1; i < 10; i++) {
        int16_t key = b[i]; int j = i - 1;
        while (j >= 0 && b[j] > key) { b[j+1] = b[j]; j--; }
        b[j+1] = key;
    }
    return b[5];   /* median */
}

uint8_t ims_detect_peaks(const int16_t *spec, uint16_t n, ims_peak_t *peaks, uint8_t max)
{
    if (n < 4 || max == 0) return 0;
    int16_t base = estimate_baseline(spec);
    int16_t maxval = -32768;
    for (int i = 0; i < (int)n; i++) if (spec[i] > maxval) maxval = spec[i];
    int16_t threshold = base + (int16_t)((maxval - base) * 3 / 20);  /* 15% of dynamic range above baseline */

    uint8_t np = 0;
    bool in_peak = false;
    int16_t peak_max = base;
    int peak_idx = 0;
    /* Simple derivative + threshold rising-edge detection */
    for (int i = 2; i < (int)n - 2; i++) {
        int16_t deriv = (int16_t)((spec[i] - spec[i-2]) / 2);
        if (!in_peak && deriv > 20 && spec[i] > threshold) {
            in_peak = true; peak_max = spec[i]; peak_idx = i;
        } else if (in_peak) {
            if (spec[i] > peak_max) { peak_max = spec[i]; peak_idx = i; }
            int16_t fall_deriv = (int16_t)((spec[i] - spec[i+2]) / 2);
            if (spec[i] < threshold + (int16_t)((maxval - base) / 10) || fall_deriv < -20) {
                /* close peak */
                if (np < max) {
                    float t_ms = IMS_T_START_MS + (float)peak_idx * (1.0f / 40.0f); /* 40 ksps -> 25 us/sample */
                    peaks[np].drift_ms = t_ms;
                    peaks[np].amplitude = peak_max - base;
                    peaks[np].k0 = 0.0f;   /* filled by caller with ambient conditions */
                }
                if (np < max) np++;
                in_peak = false;
            }
        }
    }
    if (in_peak && np < max) {
        float t_ms = IMS_T_START_MS + (float)peak_idx * (1.0f / 40.0f);
        peaks[np].drift_ms = t_ms;
        peaks[np].amplitude = peak_max - base;
        peaks[np].k0 = 0.0f;
        np++;
    }
    return np;
}

void ims_compute(float pressure_kpa, float drift_temp_c, float ambient_temp_c,
                 ims_result_t *out)
{
    if (!out) return;
    memset(out, 0, sizeof(*out));
    out->pressure_kpa = pressure_kpa;
    out->drift_temp_c = drift_temp_c;
    out->ambient_temp_c = ambient_temp_c;

    /* Build averaged spectrum from accumulator */
    int32_t div = (g_avg.count > 0) ? g_avg.count : 1;
    for (int i = 0; i < IMS_SAMPLES_PER_SWEEP; i++) {
        int32_t v = g_avg.acc[i] / div;
        if (v > 32767) v = 32767;
        if (v < -32768) v = -32768;
        out->spectrum[i] = (int16_t)v;
    }

    /* Detect peaks in drift-time domain */
    out->num_peaks = ims_detect_peaks(out->spectrum, IMS_SAMPLES_PER_SWEEP,
                                      out->peaks, IMS_MAX_PEAKS);

    /* Convert drift time -> K0 for each peak using ambient conditions.
     * Drift gas temperature: use DS18B20 wall temp if available, else ambient. */
    float t_gas = (drift_temp_c > -40.0f) ? drift_temp_c : ambient_temp_c;
    for (int i = 0; i < out->num_peaks; i++) {
        out->peaks[i].k0 = ims_k0(out->peaks[i].drift_ms, IMS_DRIFT_VOLTAGE_V,
                                  pressure_kpa, t_gas);
    }

    /* Identify reactant ion peak (RIP): closest peak to K0=2.7 */
    out->rip_present = false;
    out->reactant_k0 = 0.0f;
    float best_err = 0.3f;
    for (int i = 0; i < out->num_peaks; i++) {
        float err = fabsf(out->peaks[i].k0 - 2.70f);
        if (err < best_err) {
            best_err = err;
            out->reactant_k0 = out->peaks[i].k0;
            out->rip_present = true;
        }
    }
}