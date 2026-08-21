/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * pulser.h — High-voltage ultrasonic pulser control (HRTIM-driven)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSER_H
#define PULSER_H

#include "config.h"

typedef enum {
    PULSE_MODE_NEG_SPIKE = 0,    /* unipolar negative spike (default)     */
    PULSE_MODE_BIPOLAR,           /* bipolar spike pair                       */
    PULSE_MODE_TONE_BURST,        /* multi-cycle burst (excite narrowband)   */
} pulse_mode_t;

typedef struct {
    pulse_mode_t mode;
    uint16_t     width_ns;        /* 50–200 ns                                 */
    uint16_t     hv_voltage_mv;   /* 30000–200000 (setpoint sent to boost)    */
    uint16_t     prf_hz;          /* 10–1000                                   */
    uint8_t      burst_cycles;    /* 1–16 for tone-burst mode                  */
    uint8_t      armed;           /* 0 = safe/disabled, 1 = ready to fire      */
} pulser_config_t;

void pulser_init(void);
void pulser_configure(const pulser_config_t *cfg);
void pulser_get_config(pulser_config_t *cfg);

/* Arm/disarm the pulser. When disarmed the HV boost and driver are off. */
void pulser_arm(uint8_t armed);

/* Fire a single shot (blocking, microseconds). Used for single-shot mode. */
void pulser_fire_single(void);

/* Start/stop periodic firing at the configured PRF.
 * When running, each fire triggers an ADC capture via timer-link. */
void pulser_start_continuous(void);
void pulser_stop_continuous(void);

/* Enable HV boost converter to the requested voltage (mV). */
void pulser_set_hv(uint16_t voltage_mv);

/* Read back HV rail voltage (mV) via the monitor divider. */
uint16_t pulser_read_hv(void);

/* Safety: check probe coupling before firing (coupling test). */
uint8_t pulser_probe_coupled(void);

#endif /* PULSER_H */