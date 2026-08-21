/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * heater_safety.h — Triple-redundant heater watchdog interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SAP_WATCH_HEATER_SAFETY_H
#define SAP_WATCH_HEATER_SAFETY_H

#include <stdint.h>

void heater_safety_init(void);
int  heater_safety_fire(uint32_t pulse_ms);
int  heater_safety_has_fault(void);
void heater_safety_clear_fault(void);
uint32_t heater_safety_get_pulse_count(void);
uint32_t heater_safety_get_fault_count(void);
void heater_safety_monitor(void);

#endif /* SAP_WATCH_HEATER_SAFETY_H */