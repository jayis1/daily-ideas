/*
 * liquid.h — Peristaltic pump + rotary valve control
 */

#ifndef LIQUID_H
#define LIQUID_H

#include "config.h"

/* Pump control */
void pump_init(void);
void pump_set_rate(float ml_per_min);  /* 0 = stop */
void pump_stop(void);
float pump_get_rate(void);

/* Valve control (6-position rotary, 28BYJ-48 stepper) */
void valve_init(void);
void valve_set_position(uint8_t pos);  /* 0-5 */
uint8_t valve_get_position(void);
void valve_home(void);

/* Get valve position label */
const char *valve_position_name(uint8_t pos);

#endif /* LIQUID_H */