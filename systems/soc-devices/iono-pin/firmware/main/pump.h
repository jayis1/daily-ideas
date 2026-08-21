/*
 * pump.h — drift-gas micro-pump + 2-way valve control
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef PUMP_H
#define PUMP_H

#include <stdbool.h>
#include <stdint.h>

void pump_init(void);
void pump_set_speed(uint8_t pct);    /* 0-100 % PWM to PA5 */
uint8_t pump_get_speed(void);
void valve_set_sample(bool sample); /* true=sample path, false=purified drift-gas */
void pump_enable(bool on);

#endif /* PUMP_H */