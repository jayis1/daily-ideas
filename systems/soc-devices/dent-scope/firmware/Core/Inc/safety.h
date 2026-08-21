/*
 * dent-scope / Core/Inc/safety.h
 * Dent Scope — Safety subsystem (overload, stall, watchdog, interlock)
 * MIT License.
 */
#ifndef SAFETY_H
#define SAFETY_H

#include "main.h"

void safety_init(void);
bool safety_check(void);

#endif /* SAFETY_H */