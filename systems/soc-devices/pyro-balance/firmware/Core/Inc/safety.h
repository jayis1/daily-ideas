/*
 * pyro-balance / Core/Inc/safety.h
 */
#ifndef SAFETY_H
#define SAFETY_H
#include "main.h"
void safety_init(void);
bool safety_check(void);              /* returns false = abort */
void safety_alarm(const char* why);
void safety_pet_watchdog(void);
void safety_interlock_breach(void);
#endif