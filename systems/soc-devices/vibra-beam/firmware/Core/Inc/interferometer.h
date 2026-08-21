/*
 * interferometer.h — quadrature homodyne LDV signal processing
 */

#ifndef INTERFEROMETER_H
#define INTERFEROMETER_H

#include <stdint.h>
#include <math.h>
#include "config.h"

/* I/Q sample block */
typedef struct {
    int16_t i[CONFIG_ADC_BLOCK_SAMPLES];
    int16_t q[CONFIG_ADC_BLOCK_SAMPLES];
    uint32_t n;
} iq_block_t;

/* Unwrapped phase buffer */
typedef struct {
    float    phase_rad[CONFIG_ADC_BLOCK_SAMPLES];
    float    disp_nm[CONFIG_ADC_BLOCK_SAMPLES];
    float    vel_mms[CONFIG_ADC_BLOCK_SAMPLES];
    uint32_t n;
    float    last_phase;       /* for inter-block unwrapping */
    float    baseline_i;       /* DC baseline tracking */
    float    baseline_q;
} phase_block_t;

/* APIs */
void interferometer_init(void);
void interferometer_process(const iq_block_t *iq, phase_block_t *pb);
void interferometer_reset(void);

/* CORDIC-based atan2 wrapper (uses STM32G474 CORDIC) */
float cordic_atan2f(float y, float x);

/* Baseline (DC offset) tracking for I/Q */
void interferometer_update_baseline(const iq_block_t *iq);

#endif /* INTERFEROMETER_H */