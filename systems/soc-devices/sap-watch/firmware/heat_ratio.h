/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * heat_ratio.h — Sap-flow velocity computation interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SAP_WATCH_HEAT_RATIO_H
#define SAP_WATCH_HEAT_RATIO_H

#include "probe.h"
#include <stdint.h>

/* Set configuration (via LoRaWAN downlink) */
void heat_ratio_set_wound_factor(float f);
void heat_ratio_set_sapwood_area(float area_cm2);
void heat_ratio_set_k_xylem(float k);

/* Get current configuration */
float heat_ratio_get_sapwood_area(void);
float heat_ratio_get_wound_factor(void);
int   heat_ratio_is_zero_cal_valid(void);

/* Compute sap-flux velocity (cm/h) from a probe result */
float heat_ratio_compute_velocity(const probe_result_t *r);

/* Zero-flow calibration (run at predawn) */
void heat_ratio_run_zero_calibration(const probe_result_t *results, int count);
void heat_ratio_invalidate_zero_cal(void);

/* Convert velocity (cm/h) to whole-tree water use (L/h) */
float heat_ratio_velocity_to_flow(float v_sap_cmh);

/* Integrate sap flow over time (trapezoidal) → litres */
float heat_ratio_integrate_transpiration(const float *samples, int n, float interval_h);

/* Drought-stress detection */
void heat_ratio_record_predawn(float flux_cmh);
float heat_ratio_predawn_baseline(void);
int   heat_ratio_detect_drought_stress(float midday_flux_cmh);

/* Vapor pressure deficit (kPa) from T and RH */
float heat_ratio_compute_vpd(float air_temp_c, float rh_pct);

#endif /* SAP_WATCH_HEAT_RATIO_H */