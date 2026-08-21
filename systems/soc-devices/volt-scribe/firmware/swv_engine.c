/*
 * volt-scribe — swv_engine.c
 * Square-Wave Voltammetry engine
 *
 * Applies forward/reverse pulse pairs at each step of a staircase.
 * Measures i_forward and i_reverse, computes Δi = i_f - i_r.
 * Superior background suppression for trace analysis.
 */

#include "swv_engine.h"
#include "potentiostat.h"
#include "display.h"
#include "sd_log.h"
#include "ble_relay.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

#define SWV_MAX_POINTS 4096

static float swv_E[SWV_MAX_POINTS];
static float swv_dI[SWV_MAX_POINTS];
static float swv_iF[SWV_MAX_POINTS];
static float swv_iR[SWV_MAX_POINTS];
static int   swv_count = 0;

void swv_run(const struct params_t *p)
{
    swv_count = 0;

    printf("Running SWV: %.0f mV → %.0f mV, step=%.1f mV, amp=%.1f mV, freq=%.0f Hz\r\n",
           p->swv_start * 1000, p->swv_end * 1000,
           p->swv_step * 1000, p->swv_amplitude * 1000, p->swv_frequency);

    tia_range_t best_range = pot_auto_range();
    printf("TIA range: %s\r\n", tia_range_name(best_range));

    sdlog_open("swv");
    sdlog_write("E_V,dI_A,i_forward_A,i_reverse_A\r\n");

    float E_base = p->swv_start;
    int half_period_ms = (int)(500.0f / p->swv_frequency);
    if (half_period_ms < 1) half_period_ms = 1;

    while ((p->swv_step > 0) ? (E_base <= p->swv_end) : (E_base >= p->swv_end)) {
        /* Forward pulse: E_base + amplitude */
        float E_fwd = E_base + p->swv_amplitude;
        pot_set_voltage(E_fwd);
        HAL_Delay(half_period_ms);
        float i_forward = pot_read_current();

        /* Reverse pulse: E_base - amplitude */
        float E_rev = E_base - p->swv_amplitude;
        pot_set_voltage(E_rev);
        HAL_Delay(half_period_ms);
        float i_reverse = pot_read_current();

        /* Differential current */
        float dI = i_forward - i_reverse;

        if (swv_count < SWV_MAX_POINTS) {
            swv_E[swv_count] = E_base;
            swv_dI[swv_count] = dI;
            swv_iF[swv_count] = i_forward;
            swv_iR[swv_count] = i_reverse;
            swv_count++;
        }

        char line[80];
        snprintf(line, sizeof(line), "%.6f,%.9f,%.9f,%.9f\r\n",
                 E_base, dI, i_forward, i_reverse);
        sdlog_write(line);
        ble_relay_send_point(E_base, dI);

        extern volatile int experiment_running;
        if (!experiment_running) break;

        E_base += p->swv_step;
    }

    /* Peak detection */
    int peak_idx = 0;
    float peak_dI = 0;
    for (int i = 1; i < swv_count - 1; i++) {
        if (swv_dI[i] > peak_dI) {
            peak_dI = swv_dI[i];
            peak_idx = i;
        }
    }

    if (peak_idx > 0) {
        printf("SWV Peak: E = %.3f V, Δi = %.2f µA\r\n",
               swv_E[peak_idx], peak_dI * 1e6f);
    }

    char filename[32];
    snprintf(filename, sizeof(filename), "swv_%06d.csv", sdlog_get_sequence());
    sdlog_close(filename);
    printf("Result saved to SD: %s\r\n", filename);

    display_plot_swv(swv_E, swv_dI, swv_count);
}