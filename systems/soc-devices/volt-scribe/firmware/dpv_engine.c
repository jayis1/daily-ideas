/*
 * volt-scribe — dpv_engine.c
 * Differential Pulse Voltammetry engine
 *
 * Applies a staircase ramp with superimposed voltage pulses.
 * Measures current just before pulse (i_base) and at end of pulse (i_pulse).
 * Differential current Δi = i_pulse - i_base suppresses capacitive background.
 */

#include "dpv_engine.h"
#include "potentiostat.h"
#include "dsp.h"
#include "display.h"
#include "sd_log.h"
#include "ble_relay.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

#define DPV_MAX_POINTS 4096

static float dpv_E[DPV_MAX_POINTS];
static float dpv_dI[DPV_MAX_POINTS];
static int   dpv_count = 0;

void dpv_run(const struct params_t *p)
{
    dpv_count = 0;

    printf("Running DPV: %.0f mV → %.0f mV, step=%.1f mV, pulse=%.1f mV\r\n",
           p->dpv_start * 1000, p->dpv_end * 1000,
           p->dpv_step * 1000, p->dpv_pulse_amp * 1000);

    /* Auto-range */
    tia_range_t best_range = pot_auto_range();
    printf("TIA range: %s\r\n", tia_range_name(best_range));

    sdlog_open("dpv");
    sdlog_write("E_V,dI_A,i_base_A,i_pulse_A\r\n");

    float E = p->dpv_start;
    float step_duration = p->dpv_step / p->dpv_scan_rate;
    int pause_ms = (int)(step_duration * 1000) - (int)(p->dpv_pulse_width * 1000);
    if (pause_ms < 10) pause_ms = 10;

    while ((p->dpv_step > 0) ? (E <= p->dpv_end) : (E >= p->dpv_end)) {
        /* Base potential — measure just before pulse */
        pot_set_voltage(E);
        HAL_Delay(pause_ms);
        float i_base = pot_read_current();

        /* Apply pulse */
        float E_pulse = E + p->dpv_pulse_amp;
        pot_set_voltage(E_pulse);
        HAL_Delay((int)(p->dpv_pulse_width * 1000));
        float i_pulse = pot_read_current();

        /* Differential current */
        float dI = i_pulse - i_base;

        /* Store */
        if (dpv_count < DPV_MAX_POINTS) {
            dpv_E[dpv_count] = E;
            dpv_dI[dpv_count] = dI;
            dpv_count++;
        }

        /* Log & stream */
        char line[64];
        snprintf(line, sizeof(line), "%.6f,%.9f,%.9f,%.9f\r\n",
                 E, dI, i_base, i_pulse);
        sdlog_write(line);
        ble_relay_send_point(E, dI);

        extern volatile int experiment_running;
        if (!experiment_running) break;

        E += p->dpv_step;
    }

    /* Peak detection on Δi curve */
    int peak_idx = 0;
    float peak_dI = 0;
    for (int i = 1; i < dpv_count - 1; i++) {
        if (dpv_dI[i] > peak_dI) {
            peak_dI = dpv_dI[i];
            peak_idx = i;
        }
    }

    if (peak_idx > 0) {
        printf("DPV Peak: E = %.3f V, Δi = %.2f µA\r\n",
               dpv_E[peak_idx], peak_dI * 1e6f);
    }

    char filename[32];
    snprintf(filename, sizeof(filename), "dpv_%06d.csv", sdlog_get_sequence());
    sdlog_close(filename);
    printf("Result saved to SD: %s\r\n", filename);

    display_plot_dpv(dpv_E, dpv_dI, dpv_count);
}