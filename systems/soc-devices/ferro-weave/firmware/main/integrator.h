/*
 * integrator.h — analog integrator control
 */
#ifndef FERRO_WEAVE_INTEGRATOR_H
#define FERRO_WEAVE_INTEGRATOR_H

#include <stdbool.h>

/* Pulse the INTG_RESET line to short the integrator cap (reset drift). */
void integrator_reset(void);

/* Hold the integrator in reset (for standby / degauss disarm). */
void integrator_hold_reset(bool hold);

#endif /* FERRO_WEAVE_INTEGRATOR_H */