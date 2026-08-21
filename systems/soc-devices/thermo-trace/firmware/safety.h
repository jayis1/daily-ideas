/*
 * safety.h — Over-temperature safety watchdog (header)
 */
#ifndef SAFETY_H
#define SAFETY_H

#include <stdint.h>
#include <stdbool.h>

void    safety_init(void);
bool    safety_check(float pan_temp);
void    safety_emergency_cutoff(void);
bool    safety_is_overtemp(void);
void    safety_clear(void);

#endif /* SAFETY_H */