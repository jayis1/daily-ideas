/*
 * ionizer.h — Ni-63 / corona ionizer enable (safety-interlocked)
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef IONIZER_H
#define IONIZER_H

#include <stdbool.h>

void ionizer_init(void);
void ionizer_enable(bool on);
bool ionizer_is_enabled(void);

/* True only if all safety conditions met (interlock closed, no fault, HV ok) */
bool ionizer_safety_ok(void);

#endif /* IONIZER_H */