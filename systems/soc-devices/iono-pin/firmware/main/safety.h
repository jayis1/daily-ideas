/*
 * safety.h — Triple-redundant HV safety subsystem
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef SAFETY_H
#define SAFETY_H

#include <stdbool.h>

void safety_init(void);
bool safety_interlock_closed(void);   /* reed switch (lid closed) */
bool safety_fault(void);              /* any fault latched */
void safety_clear_fault(void);
void safety_tick(void);               /* call from main loop / IWDG refresh */
const char *safety_fault_msg(void);

#endif /* SAFETY_H */