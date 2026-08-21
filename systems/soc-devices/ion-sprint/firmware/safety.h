/*
 * safety.h — HV safety: current limit, interlock, bleeder
 */

#ifndef SAFETY_H
#define SAFETY_H

#include <stdbool.h>

/* Initialize safety peripherals */
void safety_init(void);

/* Check if HV current/voltage is within safe limits.
 * Returns true if unsafe (trip needed), false if OK. */
bool safety_check(float current_ua, float voltage_kv);

/* Check lid interlock switch (PB7). Returns true if closed (safe). */
bool safety_interlock_ok(void);

/* Check if hardware current-limit comparator (TLV3201) has tripped.
 * PC3 reads the fault output. */
bool safety_hw_trip(void);

#endif /* SAFETY_H */