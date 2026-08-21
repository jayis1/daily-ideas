/*
 * Phase Scope — Power Quality data structures
 */

#ifndef POWER_QUALITY_H
#define POWER_QUALITY_H

#include <stdint.h>

#define MAX_HARMONICS 50

typedef struct {
    /* Per-phase RMS values */
    float vrms[3];          /* V */
    float irms[3];          /* A */
    float vpeak[3];          /* V peak */
    float vmin[3];           /* V minimum (for sag detection) */
    float ipeak[3];          /* A peak */

    /* Per-phase power */
    float p[3];              /* Active power (W) */
    float q[3];              /* Reactive power (VAR) */
    float s[3];              /* Apparent power (VA) */
    float pf[3];            /* Power factor (dimensionless) */

    /* Frequency */
    float frequency;          /* Hz */

    /* Phase angles */
    float phase_vi[3];        /* Phase angle V-I (degrees) */
    float phase_v12;          /* Phase angle V1-V2 (degrees) */
    float phase_v23;          /* Phase angle V2-V3 (degrees) */

    /* Harmonics and THD */
    float harmonics_v[3][MAX_HARMONICS]; /* Voltage harmonic magnitudes */
    float harmonics_i[3][MAX_HARMONICS]; /* Current harmonic magnitudes */
    float thd_v[3];           /* Voltage THD (%) */
    float thd_i[3];           /* Current THD (%) */

    /* Environmental */
    float temperature;        /* PCB temperature (°C) */
    float vbat;              /* Battery voltage */

    /* Flags */
    uint32_t flags;           /* Overvoltage, undervoltage, transient */
    uint32_t timestamp;       /* System tick timestamp (ms) */
} power_results_t;

void power_quality_compute(power_results_t *res);

#endif /* POWER_QUALITY_H */