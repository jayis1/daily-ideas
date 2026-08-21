/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * probe.h — Heat-pulse probe interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SAP_WATCH_PROBE_H
#define SAP_WATCH_PROBE_H

#include <stdint.h>

typedef enum {
    PROBE_IDLE = 0,
    PROBE_BASELINE,
    PROBE_PULSE,
    PROBE_POSTPULSE,
    PROBE_ERROR
} probe_state_t;

typedef enum {
    PROBE_OK = 0,
    PROBE_HEATER_FAULT = -1,
    PROBE_THERM1_FAULT = -2,
    PROBE_THERM2_FAULT = -3,
    PROBE_ADC_FAULT = -4
} probe_health_t;

/* Raw measurement result from one heat-pulse cycle */
typedef struct {
    float t0_up;      /* baseline temp upstream (°C) */
    float t0_dn;      /* baseline temp downstream (°C) */
    float t1_up;      /* post-pulse max upstream (°C) */
    float t2_dn;      /* post-pulse max downstream (°C) */
    float dt_up;      /* ΔT upstream = t1_up - t0_up */
    float dt_dn;      /* ΔT downstream = t2_dn - t0_dn */
} probe_result_t;

/* Initialize probe hardware: power-gate ADC, configure ADS122U04 */
int probe_init(void);

/* Power down the analog front-end (between cycles) */
void probe_power_down(void);

/* Read one thermistor temperature (channel 0=up, 1=down). Returns °C or NAN */
float probe_read_thermistor(int channel);

/* Fire a 2 s heat pulse (hardware-timer watchdog) */
void probe_fire_heater(void);

/* Run full measurement cycle. Returns 0 on success, <0 on error. */
int probe_run_cycle(probe_result_t *result);

/* Get current probe state */
probe_state_t probe_get_state(void);

/* Health check: heater overcurrent, thermistor continuity */
int probe_check_health(void);

#endif /* SAP_WATCH_PROBE_H */