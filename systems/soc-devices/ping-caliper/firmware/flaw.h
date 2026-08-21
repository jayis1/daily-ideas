/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * flaw.h — Gate-based flaw detection and equivalent sizing
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef FLAW_H
#define FLAW_H

#include "config.h"
#include "receiver.h"

typedef struct {
    uint16_t start_us;   /* gate start (depth in µs)                    */
    uint16_t width_us;   /* gate width (µs)                              */
    uint16_t threshold;  /* detection threshold (12-bit ADC count, 0..4095) */
    uint8_t  enabled;    /* 1 = gate active                              */
} flaw_gate_t;

typedef struct {
    uint8_t  detected;     /* 1 = a flaw was found in the gate           */
    int16_t  peak_index;   /* sample index of the flaw peak              */
    float    depth_mm;    /* flaw depth from surface                     */
    float    peak_amp;   /* normalized amplitude (0..1)                  */
    float    equiv_mm;   /* equivalent flat-bottom-hole size (DGS est.)  */
} flaw_result_t;

void flaw_init(void);
void flaw_set_gate(const flaw_gate_t *gate);
void flaw_get_gate(flaw_gate_t *gate);

/* Evaluate the gate on an A-scan envelope. */
void flaw_evaluate(const ascan_t *scan,
                    const thickness_result_t *thk,
                    flaw_result_t *out);

/* DGS (distance–gain–size) simplified equivalent size estimate.
 * Uses a stored near-field / beam-spread model for the active probe. */
float flaw_dgs_equiv(float depth_mm, float peak_amp, float freq_mhz, float elem_mm);

#endif /* FLAW_H */