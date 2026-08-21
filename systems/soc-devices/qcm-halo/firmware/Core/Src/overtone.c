/*
 * overtone.c — Multi-overtone measurement sequencing
 */

#include "main.h"
#include <string.h>
#include "overtone.h"
#include "qcm_driver.h"

const uint8_t overtone_multipliers[QCM_OVERtones] = {1, 3, 5, 7, 9, 11};

float overtone_freq(float f0, uint8_t idx)
{
    if (idx >= QCM_OVERtones) return f0;
    return f0 * overtone_multipliers[idx];
}

const char *overtone_label(uint8_t idx)
{
    static const char *labels[] = {"1st", "3rd", "5th", "7th", "9th", "11th"};
    if (idx >= QCM_OVERtones) return "?";
    return labels[idx];
}

int overtone_sweep(uint8_t channel, float temperature, overtone_sweep_t *sweep)
{
    memset(sweep, 0, sizeof(*sweep));
    sweep->temperature = temperature;
    sweep->timestamp = HAL_GetTick();

    for (uint8_t i = 0; i < QCM_OVERtones; i++) {
        qcm_result_t r = qcm_measure(channel, i, temperature, 1, 0);
        if (!r.valid) return -1;

        sweep->freq[i] = r.frequency;
        sweep->delta_f[i] = r.delta_f;
        sweep->delta_d[i] = r.delta_d;
        sweep->dissipation[i] = r.dissipation;
    }

    return 0;
}