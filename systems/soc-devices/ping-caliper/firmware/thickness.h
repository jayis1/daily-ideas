/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * thickness.h — Time-of-flight thickness & echo-to-echo computation
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef THICKNESS_H
#define THICKNESS_H

#include "config.h"
#include "receiver.h"

typedef enum {
    MEASURE_MODE_PULSE_ECHO = 0,   /* surface-to-backwall TOF             */
    MEASURE_MODE_ECHO_ECHO,        /* B1-to-B2 TOF (through-coating)      */
    MEASURE_MODE_FLAW,             /* gate-based flaw detection           */
} measure_mode_t;

typedef struct {
    measure_mode_t mode;
    uint32_t       velocity_mps;   /* material longitudinal velocity      */
    uint16_t       zero_offset_ns; /* delay-line / probe zero offset (ns) */
    float          thickness_mm;   /* computed result                     */
    float          tof_ns;         /* raw time-of-flight (ns)             */
    uint8_t        valid;          /* 1 = a valid measurement was made    */
    int8_t         peak_index;     /* sample index of back-wall echo      */
    float          peak_amp;       /* normalized peak amplitude (0..1)    */
} thickness_result_t;

/* Compute thickness from an A-scan envelope. */
void thickness_compute(const ascan_t *scan,
                        const thickness_result_t *prev,
                        thickness_result_t *out);

/* Echo-to-echo: find B1 and B2 and measure their spacing. */
void thickness_echo_echo(const ascan_t *scan,
                          const thickness_result_t *prev,
                          thickness_result_t *out);

/* Parabolic-interpolation peak refinement for sub-sample timing. */
float thickness_parabolic_interp(uint16_t y0, uint16_t y1, uint16_t y2);

/* Convert sample index → time-of-flight (ns) given sample rate. */
float thickness_index_to_tof(int16_t idx, uint16_t sample_count, uint16_t window_us);

/* Convert TOF (ns) → thickness (mm) given velocity (m/s). */
float thickness_tof_to_mm(float tof_ns, uint32_t velocity_mps);

#endif /* THICKNESS_H */