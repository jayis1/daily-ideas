/*
 * shutter.h — Bradbury-Nielsen shutter grid control
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef SHUTTER_H
#define SHUTTER_H

#include <stdint.h>
#include <stdbool.h>

void shutter_init(void);
void shutter_set_rep_rate_hz(uint32_t hz);   /* 20-40 Hz */
uint32_t shutter_get_rep_rate(void);
void shutter_arm(bool on);                    /* start/stop shutter pulsing */
void shutter_trigger_pulse(void);             /* single 200us pulse */
bool shutter_is_armed(void);

#endif /* SHUTTER_H */