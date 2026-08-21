/*
 * volt-scribe — amperometric.c
 * Amperometric i-t mode: constant potential, record current vs. time
 * Used for biosensor readout, chronoamperometry, etc.
 */

#include "amperometric.h"
#include "potentiostat.h"
#include "display.h"
#include "sd_log.h"
#include "ble_relay.h"
#include <math.h>
#include <stdio.h>

#define AMP_MAX_POINTS 65536

void amperometric_run(const struct params_t *p)
{
    printf("Running i-t at %.0f mV for %.0f s @ %.1f Hz\r\n",
           p->amp_potential * 1000, p->amp_duration, p->amp_sample_rate);

    tia_range_t best_range = pot_auto_range();
    printf("TIA range: %s\r\n", tia_range_name(best_range));

    pot_set_voltage(p->amp_potential);
    HAL_Delay(100);  /* Settle */

    sdlog_open("amp");
    sdlog_write("time_s,I_A,E_V\r\n");

    int total_samples = (int)(p->amp_duration * p->amp_sample_rate);
    int sample_interval_ms = (int)(1000.0f / p->amp_sample_rate);

    float i_sum = 0;
    int i_count = 0;

    for (int i = 0; i < total_samples; i++) {
        float t = (float)i / p->amp_sample_rate;
        float I = pot_read_current();
        float E = pot_read_potential();

        i_sum += I;
        i_count++;

        char line[64];
        snprintf(line, sizeof(line), "%.4f,%.9f,%.6f\r\n", t, I, E);
        sdlog_write(line);
        ble_relay_send_point(t, I);

        /* Update display every 10 samples */
        if (i % 10 == 0) {
            display_plot_it(t, I);
        }

        HAL_Delay(sample_interval_ms);

        extern volatile int experiment_running;
        if (!experiment_running) break;
    }

    float i_avg = i_sum / (float)i_count;
    printf("Average current: %.2f µA\r\n", i_avg * 1e6f);

    char filename[32];
    snprintf(filename, sizeof(filename), "it_%06d.csv", sdlog_get_sequence());
    sdlog_close(filename);
    printf("Result saved to SD: %s\r\n", filename);
}

void galvanostatic_run(const struct params_t *p)
{
    printf("Running galvanostatic at %.2f µA for %.0f s\r\n",
           p->galv_current * 1e6f, p->galv_duration);

    /* In galvanostatic mode, we set a constant current and measure voltage.
     * This requires adjusting the potentiostat voltage in a feedback loop
     * to maintain the target current. */

    sdlog_open("galv");
    sdlog_write("time_s,E_V,I_A\r\n");

    int total_samples = (int)(p->galv_duration * 10.0f);  /* 10 Hz */
    float target_I = p->galv_current;
    float current_V = 0.0f;
    float Kp = 0.01f;  /* Proportional gain for current control */

    for (int i = 0; i < total_samples; i++) {
        float t = (float)i / 10.0f;

        /* PI control: adjust voltage to maintain target current */
        float I = pot_read_current();
        float error = target_I - I;
        current_V += Kp * error;

        /* Clamp voltage */
        if (current_V > 2.048f) current_V = 2.048f;
        if (current_V < -2.048f) current_V = -2.048f;

        pot_set_voltage(current_V);
        float E = pot_read_potential();

        char line[64];
        snprintf(line, sizeof(line), "%.2f,%.6f,%.9f\r\n", t, E, I);
        sdlog_write(line);
        ble_relay_send_point(t, E);

        HAL_Delay(100);

        extern volatile int experiment_running;
        if (!experiment_running) break;
    }

    char filename[32];
    snprintf(filename, sizeof(filename), "galv_%06d.csv", sdlog_get_sequence());
    sdlog_close(filename);
    printf("Result saved to SD: %s\r\n", filename);
}