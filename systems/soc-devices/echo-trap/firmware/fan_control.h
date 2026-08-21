/*
 * fan_control.h — Suction fan trap control (DRV8601 PWM soft-start)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_FAN_CONTROL_H
#define ECHO_TRAP_FAN_CONTROL_H

#include <stdint.h>
#include <stdbool.h>

void fan_control_init(void);
void fan_control_capture(uint16_t duration_ms);
void fan_control_off(void);
bool fan_control_check_fault(void);

#endif /* ECHO_TRAP_FAN_CONTROL_H */