/*
 * overtone.h — Multi-overtone measurement sequencing
 */

#ifndef OVERTONE_H
#define OVERTONE_H

#include "config.h"

extern const uint8_t overtone_multipliers[QCM_OVERtones];

/* Get overtone frequency for fundamental f0 and index */
float overtone_freq(float f0, uint8_t idx);

/* Get overtone label string (e.g., "3rd") */
const char *overtone_label(uint8_t idx);

/* Full overtone sweep: measure Δf and ΔD at all overtones for one channel */
typedef struct {
    float freq[QCM_OVERtones];
    float delta_f[QCM_OVERtones];
    float delta_d[QCM_OVERtones];
    float dissipation[QCM_OVERtones];
    float temperature;
    uint32_t timestamp;
} overtone_sweep_t;

int overtone_sweep(uint8_t channel, float temperature, overtone_sweep_t *sweep);

#endif /* OVERTONE_H */