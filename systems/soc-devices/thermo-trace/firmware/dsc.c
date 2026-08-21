/*
 * dsc.c — DSC heat flow computation and peak detection
 *
 * In power-compensation DSC, heat flow = electrical power difference:
 *   Φ(t) = P_sample(t) - P_reference(t)  [mW]
 *
 * Peak detection: derivative-based, finds local extrema in the
 * heat-flow signal after baseline subtraction. For each peak:
 *   - Onset temperature: extrapolated intersection of pre-peak baseline
 *     and steepest tangent
 *   - Peak temperature: temperature at extremum
 *   - Enthalpy: integral of (Φ - baseline) dt, divided by sample mass
 *
 * Glass transition detection: step change in heat flow detected by
 * finding inflection points (zero of 2nd derivative).
 */

#include "dsc.h"
#include <math.h>
#include <string.h>

void dsc_init(dsc_scan_t *scan) {
    memset(scan, 0, sizeof(dsc_scan_t));
    scan->sample_mass = 5.0f;  /* default 5 mg */
}

void dsc_clear(dsc_scan_t *scan) {
    scan->count = 0;
    scan->num_peaks = 0;
    scan->num_transitions = 0;
    scan->baseline_start = 0.0f;
    scan->baseline_end = 0.0f;
}

void dsc_add_point(dsc_scan_t *scan, float temp, float heat_flow, float time) {
    if (scan->count >= DSC_BUFFER_SIZE) return;
    dsc_point_t *pt = &scan->buffer[scan->count];
    pt->temp = temp;
    pt->heat_flow = heat_flow;
    pt->time = time;
    scan->count++;
}

void dsc_compute_heat_flow(float p_sample, float p_ref,
                            float v_supply,
                            float duty_s, float duty_r,
                            float *heat_flow_mw) {
    /* Compute actual power delivered to each heater */
    float r_heater = HEATER_R_OHM;
    float ps = (v_supply * v_supply / r_heater) * duty_s;
    float pr = (v_supply * v_supply / r_heater) * duty_r;
    /* Heat flow: positive = endothermic (sample needs more power) */
    float phi = ps - pr;
    /* Convert W to mW */
    *heat_flow_mw = phi * 1000.0f;
}

void dsc_compute_baseline(dsc_scan_t *scan) {
    if (scan->count < 10) return;
    /* Average first 10 and last 10 points for baseline */
    float sum = 0.0f;
    for (uint32_t i = 0; i < 10 && i < scan->count; i++)
        sum += scan->buffer[i].heat_flow;
    scan->baseline_start = sum / 10.0f;

    sum = 0.0f;
    for (uint32_t i = scan->count - 10; i < scan->count; i++)
        sum += scan->buffer[i].heat_flow;
    scan->baseline_end = sum / 10.0f;
}

static float interp_baseline(dsc_scan_t *scan, uint32_t idx) {
    if (scan->count < 2) return scan->baseline_start;
    float frac = (float)idx / (float)(scan->count - 1);
    return scan->baseline_start +
           frac * (scan->baseline_end - scan->baseline_start);
}

void dsc_detect_peaks(dsc_scan_t *scan) {
    dsc_compute_baseline(scan);
    if (scan->count < 20) return;

    /* Compute 1st and 2nd derivatives */
    float d1[DSC_BUFFER_SIZE];
    float d2[DSC_BUFFER_SIZE];

    for (uint32_t i = 2; i < scan->count - 2; i++) {
        /* 1st derivative (heat flow w.r.t. temperature) */
        float dt_temp = scan->buffer[i+1].temp - scan->buffer[i-1].temp;
        if (fabsf(dt_temp) < 1e-6f) dt_temp = 1e-6f;
        float dy = scan->buffer[i+1].heat_flow - scan->buffer[i-1].heat_flow;
        d1[i] = dy / dt_temp;
    }

    for (uint32_t i = 3; i < scan->count - 3; i++) {
        /* 2nd derivative */
        d2[i] = d1[i+1] - d1[i-1];
    }

    /* Peak detection: local extrema in baseline-subtracted heat flow */
    scan->num_peaks = 0;
    float threshold = 0.05f;  /* mW minimum peak height */

    for (uint32_t i = 4; i < scan->count - 4; i++) {
        if (scan->num_peaks >= MAX_PEAKS) break;

        float hf = scan->buffer[i].heat_flow;
        float hf_prev = scan->buffer[i-1].heat_flow;
        float hf_next = scan->buffer[i+1].heat_flow;

        /* Endothermic peak (positive: sample needs more power) */
        if (hf > hf_prev && hf >= hf_next && hf > threshold) {
            dsc_peak_t *pk = &scan->peaks[scan->num_peaks];
            pk->type = PEAK_ENDOTHERMIC;
            pk->peak_temp = scan->buffer[i].temp;
            pk->height = hf;

            /* Find onset: backtrack to where derivative crosses zero */
            uint32_t onset_idx = i;
            for (uint32_t j = i; j > 2; j--) {
                if (d1[j] <= 0.0f || j < 2) {
                    onset_idx = j;
                    break;
                }
            }
            pk->onset_temp = scan->buffer[onset_idx].temp;

            /* Find end: forward-track to where derivative crosses zero */
            uint32_t end_idx = i;
            for (uint32_t j = i; j < scan->count - 2; j++) {
                if (d1[j] >= 0.0f) {
                    end_idx = j;
                    break;
                }
            }
            pk->end_temp = scan->buffer[end_idx].temp;

            /* Enthalpy: integrate (hf - baseline) over time */
            pk->enthalpy = dsc_integrate_peak(scan, scan->num_peaks);

            scan->num_peaks++;
        }

        /* Exothermic peak (negative: sample releases heat, needs less power) */
        if (hf < hf_prev && hf <= hf_next && hf < -threshold) {
            dsc_peak_t *pk = &scan->peaks[scan->num_peaks];
            pk->type = PEAK_EXOTHERMIC;
            pk->peak_temp = scan->buffer[i].temp;
            pk->height = hf;  /* negative */

            uint32_t onset_idx = i;
            for (uint32_t j = i; j > 2; j--) {
                if (d1[j] >= 0.0f || j < 2) {
                    onset_idx = j;
                    break;
                }
            }
            pk->onset_temp = scan->buffer[onset_idx].temp;

            uint32_t end_idx = i;
            for (uint32_t j = i; j < scan->count - 2; j++) {
                if (d1[j] <= 0.0f) {
                    end_idx = j;
                    break;
                }
            }
            pk->end_temp = scan->buffer[end_idx].temp;

            pk->enthalpy = dsc_integrate_peak(scan, scan->num_peaks);
            scan->num_peaks++;
        }
    }

    /* Glass transition detection: inflection point in heat flow
       (zero of 2nd derivative, step change) */
    scan->num_transitions = 0;
    for (uint32_t i = 5; i < scan->count - 5; i++) {
        if (scan->num_transitions >= MAX_TRANSITIONS) break;
        /* Look for sign change in d2 near a significant step */
        if (d2[i] * d2[i+1] < 0.0f) {
            /* Potential inflection point — check if it's a step (Tg) */
            float step = scan->buffer[i+10].heat_flow -
                         scan->buffer[i-10].heat_flow;
            if (fabsf(step) > 0.02f && fabsf(step) < 2.0f) {
                /* Tg = mid-point of step */
                dsc_peak_t *t = &scan->transitions[scan->num_transitions];
                t->type = PEAK_GLASS_TRANSITION;
                t->peak_temp = scan->buffer[i].temp;
                t->onset_temp = scan->buffer[i-5].temp;
                t->end_temp = scan->buffer[i+5].temp;
                t->height = step;
                t->delta_cp = fabsf(step) / (5.0f * scan->sample_mass);
                scan->num_transitions++;
            }
        }
    }
}

float dsc_integrate_peak(dsc_scan_t *scan, uint8_t peak_idx) {
    if (peak_idx >= scan->num_peaks) return 0.0f;
    dsc_peak_t *pk = &scan->peaks[peak_idx];

    /* Find indices corresponding to onset and end temps */
    uint32_t start_idx = 0, end_idx = 0;
    for (uint32_t i = 0; i < scan->count; i++) {
        if (scan->buffer[i].temp >= pk->onset_temp) { start_idx = i; break; }
    }
    for (uint32_t i = start_idx; i < scan->count; i++) {
        if (scan->buffer[i].temp >= pk->end_temp) { end_idx = i; break; }
    }
    if (end_idx <= start_idx) return 0.0f;

    /* Trapezoidal integration of (hf - baseline) over time */
    float integral = 0.0f;
    for (uint32_t i = start_idx; i < end_idx; i++) {
        float dt = scan->buffer[i+1].time - scan->buffer[i].time;
        float hf0 = scan->buffer[i].heat_flow - interp_baseline(scan, i);
        float hf1 = scan->buffer[i+1].heat_flow - interp_baseline(scan, i+1);
        integral += 0.5f * (hf0 + hf1) * dt;
    }

    /* Convert mW·s to J (1 mW·s = 1 mJ = 0.001 J),
       then divide by sample mass (mg → g) */
    float mass_g = scan->sample_mass / 1000.0f;
    if (mass_g > 0.0f) {
        return (integral * 0.001f) / mass_g;  /* J/g */
    }
    return integral * 0.001f;
}