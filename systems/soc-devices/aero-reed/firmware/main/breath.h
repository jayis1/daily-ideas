/*
 * breath.h — breath pressure sensor
 */
#pragma once
#include <stdint.h>
#include <stdbool.h>

void   breath_init(void);
void   breath_scan(void);             /* call from sensor task */
uint8_t breath_get_velocity(void);   /* 0..127 MIDI velocity */
bool   breath_get_gate(void);        /* true above threshold */
float  breath_get_pressure_kpa(void);/* raw pressure for display */