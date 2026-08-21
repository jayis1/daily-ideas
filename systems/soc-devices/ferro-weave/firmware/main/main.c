/*
 * main.c — Ferro Weave firmware entry (STM32G474RET6)
 *
 * Orchestrates the full sweep cycle: degauss → arm → ramp → hold →
 * capture → compute → log → disarm. The sweep runs in the main loop
 * (a cooperative state machine driven by sweep_get_status()); sensor
 * polling (buttons, temperature, fuel gauge) happens in a separate
 * thread-like super-loop pass. The hard real-time path (HRTIM + ADC
 * DMA + integrator reset) is driven by hardware, not by this loop.
 */
#include "sweep.h"
#include "adc.h"
#include "integrator.h"
#include "bh.h"
#include "power.h"
#include "display.h"
#include "sdlog.h"
#include "esp_link.h"

#include <string.h>
#include <stdio.h>
#include <math.h>

static const char *TAG = "ferro";

/* Active geometry — defaults for a standard 3E25 ferrite toroid
 * (TDK B64290L0678X038), overwritten by commands from the ESP32-C3. */
static geom_t g_geom = {
    .n1 = 100, .n2 = 100,
    .l_e = 0.0785f,       /* 78.5 mm magnetic path length    */
    .a2 = 31.4e-6f,       /* 31.4 mm² winding area            */
    .a_core = 31.4e-6f,   /* ≈ winding area for a close-fit  */
    .rho = 4800.0f,       /* 3E25 ~ 4800 kg/m³               */
    .freq = 10.0f,
};

static sweep_params_t g_params;
static bh_result_t    g_result;
static float g_H[ADC_BUF_LEN];
static float g_B[ADC_BUF_LEN];

int main(void)
{
    /* HAL init, system clock 170 MHz, peripherals. */
    power_init();
    adc_init();
    display_init();
    esp_link_init();
    sdlog_mount();
    sweep_defaults(&g_params);

    display_status("Ferro Weave", "ready");
    esp_link_send_status("boot ready");

    int  sweep_requested = 0;
    int  mode_idx = 0;
    const sweep_waveform_t modes[3] = { SWEEP_SIN, SWEEP_TRI, SWEEP_DC };

    for (;;) {
        /* ── Button polling ─────────────────────────────────────── */
        char cmd[64];
        if (esp_link_poll_cmd(cmd, sizeof(cmd)) > 0) {
            /* Simple text commands from the ESP32-C3 / app:
             *   SWEEP
             *   WAVE SIN|TRI|DC
             *   IPEAK 1.0
             *   FREQ 10
             *   GEOM N1 N2 LE A2 ACORE RHO
             */
            if (strncmp(cmd, "SWEEP", 5) == 0) {
                sweep_requested = 1;
            } else if (strncmp(cmd, "WAVE SIN", 8) == 0)  g_params.waveform = SWEEP_SIN;
            else if (strncmp(cmd, "WAVE TRI", 8) == 0)    g_params.waveform = SWEEP_TRI;
            else if (strncmp(cmd, "WAVE DC",  7) == 0)    g_params.waveform = SWEEP_DC;
            else if (strncmp(cmd, "IPEAK", 5) == 0)       sscanf(cmd + 5, "%f", &g_params.i_peak);
            else if (strncmp(cmd, "FREQ", 4) == 0)        sscanf(cmd + 4, "%f", &g_params.freq);
            else if (strncmp(cmd, "GEOM", 4) == 0) {
                sscanf(cmd + 4, "%hu %hu %f %f %f %f",
                       &g_geom.n1, &g_geom.n2, &g_geom.l_e,
                       &g_geom.a2, &g_geom.a_core, &g_geom.rho);
            }
        }

        if (sweep_requested && sweep_get_status() == SWEEP_IDLE) {
            sweep_requested = 0;
            g_geom.freq = g_params.freq;
            sweep_start(&g_params);
        }

        /* ── Sweep state machine ───────────────────────────────── */
        sweep_state_t st = sweep_get_status();
        switch (st) {
        case SWEEP_DEGAUSS:
            power_amp_enable(true);
            integrator_hold_reset(true);
            break;
        case SWEEP_ARM:
            integrator_hold_reset(false);
            integrator_reset();
            break;
        case SWEEP_CAPTURE:
            adc_arm_capture();
            if (adc_wait_capture(2000)) {
                adc_to_engineering(adc_raw_i, adc_raw_b, ADC_BUF_LEN,
                                   g_H, g_B);
                /* Convert current I to field H = N1·I/l_e */
                float k = (float)g_geom.n1 / g_geom.l_e;
                for (int i = 0; i < ADC_BUF_LEN; i++) g_H[i] *= k;
            }
            break;
        case SWEEP_COMPUTE:
            bh_compute(g_H, g_B, ADC_BUF_LEN, &g_geom, &g_result);
            display_plot_loop(g_H, g_B, ADC_BUF_LEN, &g_result);
            break;
        case SWEEP_LOG:
            sdlog_write(&g_params, &g_geom, g_H, g_B, ADC_BUF_LEN,
                        &g_result);
            esp_link_send_sweep(&g_params, &g_geom, g_H, g_B,
                                ADC_BUF_LEN, &g_result);
            break;
        case SWEEP_DISARM:
            integrator_hold_reset(true);
            power_amp_enable(false);
            break;
        case SWEEP_DONE:
            display_status("done", "ready");
            esp_link_send_status("sweep done");
            break;
        case SWEEP_FAULT:
            power_amp_enable(false);
            display_status("FAULT", "OCP/thermal");
            esp_link_send_status("fault");
            break;
        default:
            break;
        }

        /* ── MODE button cycles waveform (sim poll) ────────────── */
        /* (firmware reads GPIO; omitted here for brevity) */
        (void)mode_idx; (void)modes;

        /* ── Periodic status ───────────────────────────────────── */
        /* Every ~1 s send battery / temp to the ESP32-C3. */
        /* (throttled by a tick counter in the real firmware) */
    }
    return 0;
}