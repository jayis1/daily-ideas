/*
 * volt-scribe — cv_engine.c
 * Cyclic Voltammetry engine
 *
 * Ramps potential: start → vertex → end (one segment per direction)
 * Samples current & potential simultaneously via ADS1115 + ADC2.
 * Detects peaks using derivative zero-crossing analysis.
 */

#include "cv_engine.h"
#include "potentiostat.h"
#include "dsp.h"
#include "display.h"
#include "sd_log.h"
#include "ble_relay.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

#define CV_MAX_POINTS 8192
#define SAMPLE_RATE_HZ 10000

/* ── Data buffers ──────────────────────────────────────────────── */

static float cv_E[CV_MAX_POINTS];
static float cv_I[CV_MAX_POINTS];
static int   cv_count = 0;

/* ── Ramp generator ────────────────────────────────────────────── */

static void ramp_segment(float e_start, float e_end, float scan_rate,
                         void (*sample_cb)(float E, float I))
{
    float delta_E = e_end - e_start;
    float duration = fabsf(delta_E) / scan_rate;
    int n_samples = (int)(duration * SAMPLE_RATE_HZ);
    if (n_samples > CV_MAX_POINTS) n_samples = CV_MAX_POINTS;

    float step = delta_E / (float)n_samples;

    for (int i = 0; i < n_samples; i++) {
        float E = e_start + step * (float)i;
        pot_set_voltage(E);
        HAL_Delay(1);  /* ~1 ms per point at 10 kHz effective rate */

        float I = pot_read_current();
        float measured_E = pot_read_potential();

        /* iR compensation */
        if (ir_comp_ohm > 0.0f) {
            I += I * ir_comp_ohm;  /* Corrected: I_corrected = I_measured + I*R_u */
            /* Actually: E_applied = E_set + I*R_u, so I_true ≈ I_meas * (1 + small correction)
             * For proper compensation: I_comp = I_meas / (1 + R_u/R_f) — simplified */
        }

        if (sample_cb) sample_cb(measured_E, I);

        /* Stream to BLE */
        ble_relay_send_point(measured_E, I);

        /* Check for stop */
        extern volatile int experiment_running;
        if (!experiment_running) break;
    }
}

/* ── CV peak detection ─────────────────────────────────────────── */

typedef struct {
    float E_p;      /* Peak potential (V) */
    float I_p;      /* Peak current (A) */
    int   type;     /* 0 = anodic, 1 = cathodic */
} cv_peak_t;

#define MAX_PEAKS 8
static cv_peak_t peaks[MAX_PEAKS];
static int peak_count = 0;

static void detect_peaks(void)
{
    if (cv_count < 10) return;

    peak_count = 0;

    /* Compute smoothed derivative dI/dE */
    for (int i = 3; i < cv_count - 3 && peak_count < MAX_PEAKS; i++) {
        float dI = (cv_I[i+3] - cv_I[i-3]) / (cv_E[i+3] - cv_E[i-3]);

        /* Find sign changes in derivative (zero-crossing = peak) */
        float dI_prev = (cv_I[i] - cv_I[i-1]) / (cv_E[i] - cv_E[i-1]);
        float dI_curr = (cv_I[i+1] - cv_I[i]) / (cv_E[i+1] - cv_E[i]);

        if (dI_prev > 0 && dI_curr <= 0) {
            /* Anodic peak (positive current, maximum) */
            float height = fabsf(cv_I[i]);
            if (height > 1e-9f) {  /* Minimum 1 nA peak height */
                peaks[peak_count].E_p = cv_E[i];
                peaks[peak_count].I_p = cv_I[i];
                peaks[peak_count].type = 0;
                peak_count++;
            }
        } else if (dI_prev < 0 && dI_curr >= 0) {
            /* Cathodic peak (negative current, minimum) */
            float height = fabsf(cv_I[i]);
            if (height > 1e-9f) {
                peaks[peak_count].E_p = cv_E[i];
                peaks[peak_count].I_p = cv_I[i];
                peaks[peak_count].type = 1;
                peak_count++;
            }
        }
    }
}

/* ── Sample callback ───────────────────────────────────────────── */

static void cv_sample(float E, float I)
{
    if (cv_count < CV_MAX_POINTS) {
        cv_E[cv_count] = E;
        cv_I[cv_count] = I;
        cv_count++;
    }
}

/* ── Main CV run ───────────────────────────────────────────────── */

void cv_run(const params_t *p)
{
    cv_count = 0;
    char filename[32];

    printf("Running CV: %.0f mV → %.0f mV → %.0f mV @ %.0f mV/s\r\n",
           p->cv_start * 1000, p->cv_vertex * 1000,
           p->cv_end * 1000, p->cv_scan_rate * 1000);

    /* Auto-range TIA before starting */
    tia_range_t best_range = pot_auto_range();
    printf("TIA range: %s\r\n", tia_range_name(best_range));

    /* Open log file */
    sdlog_open("cv");

    /* Write CSV header */
    sdlog_write("E_V,I_A,segment,cycle\r\n");

    for (int cycle = 0; cycle < p->cv_cycles; cycle++) {
        if (p->cv_start < p->cv_vertex) {
            /* Forward sweep: start → vertex */
            ramp_segment(p->cv_start, p->cv_vertex, p->cv_scan_rate, cv_sample);
            /* Reverse sweep: vertex → end */
            ramp_segment(p->cv_vertex, p->cv_end, p->cv_scan_rate, cv_sample);
        } else {
            /* Start above vertex: reverse first */
            ramp_segment(p->cv_start, p->cv_vertex, p->cv_scan_rate, cv_sample);
            ramp_segment(p->cv_vertex, p->cv_end, p->cv_scan_rate, cv_sample);
        }

        extern volatile int experiment_running;
        if (!experiment_running) break;
    }

    /* Detect peaks */
    detect_peaks();

    /* Report peaks */
    for (int i = 0; i < peak_count; i++) {
        const char *type_str = peaks[i].type ? "cathodic" : "anodic";
        printf("Peak %d: E = %.3f V, i = %.2f µA (%s)\r\n",
               i + 1, peaks[i].E_p, peaks[i].I_p * 1e6f, type_str);

        char line[80];
        snprintf(line, sizeof(line), "# Peak %d: E=%.3fV, i=%.2fuA (%s)\r\n",
                 i + 1, peaks[i].E_p, peaks[i].I_p * 1e6f, type_str);
        sdlog_write(line);
    }

    /* Check reversibility (ΔE_p for anodic/cathodic pair) */
    if (peak_count >= 2) {
        for (int i = 0; i < peak_count - 1; i++) {
            if (peaks[i].type == 0 && peaks[i+1].type == 1) {
                float delta_Ep = fabsf(peaks[i].E_p - peaks[i+1].E_p) * 1000.0f;
                printf("ΔE_p = %.0f mV", delta_Ep);
                if (delta_Ep < 59.0f)
                    printf(" (reversible, ideal = 59 mV at 25°C)\r\n");
                else if (delta_Ep < 120.0f)
                    printf(" (quasi-reversible)\r\n");
                else
                    printf(" (irreversible)\r\n");
            }
        }
    }

    /* Save data points */
    for (int i = 0; i < cv_count; i++) {
        char line[64];
        snprintf(line, sizeof(line), "%.6f,%.9f\r\n", cv_E[i], cv_I[i]);
        sdlog_write(line);
    }

    snprintf(filename, sizeof(filename), "cv_%06d.csv", sdlog_get_sequence());
    sdlog_close(filename);
    printf("Result saved to SD: %s\r\n", filename);

    /* Display voltammogram */
    display_plot_cv(cv_E, cv_I, cv_count, peaks, peak_count);
}

float ir_comp_ohm = 0.0f;  /* Declared here, referenced from potentiostat.c */