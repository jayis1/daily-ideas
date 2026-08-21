/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * tgc.h — Time-gain compensation (TGC) ramp generation via DAC + DMA
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef TGC_H
#define TGC_H

#include "config.h"

typedef enum {
    TGC_SHAPE_FLAT    = 0,    /* constant gain (no compensation)          */
    TGC_SHAPE_LINEAR,         /* gain rises linearly with time/depth       */
    TGC_SHAPE_EXPONENTIAL,    /* exponential rise (compensates attenuation) */
    TGC_SHAPE_CUSTOM,         /* user-defined 256-point curve              */
} tgc_shape_t;

typedef struct {
    tgc_shape_t shape;
    float       start_db;       /* gain at t=0 (surface)                     */
    float       end_db;         /* gain at end of window (max depth)         */
    uint16_t    window_us;      /* TGC window length in µs                   */
    uint8_t     lna_gain_idx;   /* 0=low, 1=mid, 2=high (AD8331 LNA pins)    */
} tgc_config_t;

void tgc_init(void);
void tgc_configure(const tgc_config_t *cfg);
void tgc_get_config(tgc_config_t *cfg);

/* Set a single point in the custom curve (0..255). */
void tgc_set_curve_point(uint16_t idx, float gain_db);

/* Start the TGC ramp synchronized with the next transmit pulse.
 * The DAC DMA is triggered by the HRTIM master timer so the ramp
 * always restarts in lockstep with the pulser. */
void tgc_arm(void);
void tgc_disarm(void);

/* Convert dB → AD8331 control voltage (0..1 V → 0..4095 DAC). */
uint16_t tgc_db_to_dac(float gain_db);

/* Convert DAC code → dB (inverse). */
float tgc_dac_to_db(uint16_t dac);

#endif /* TGC_H */