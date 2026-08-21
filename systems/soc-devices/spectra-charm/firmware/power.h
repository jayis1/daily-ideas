/*
 * Spectra Charm — power.h
 */
#ifndef POWER_H
#define POWER_H

#include <stdint.h>
#include <stdbool.h>

void Power_EnterDeepSleep(void);
void Power_EnterSleep(void);
void Power_EnterIdle(void);
void Power_Wakeup(void);
void Power_Tick(uint32_t elapsed_ms);
bool Power_IsLowBattery(void);

#endif