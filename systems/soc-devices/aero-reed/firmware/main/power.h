/*
 * power.h — battery / fuel gauge / charging
 */
#pragma once
#include <stdint.h>
#include <stdbool.h>

void   power_init(void);
void   power_task(void *arg);
uint8_t power_get_battery_pct(void);
bool   power_is_charging(void);