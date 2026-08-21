/*
 * Sap Watch — Tree Sap-Flow Monitor
 * STM32WL55JC Firmware
 *
 * power.h — Power management interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef SAP_WATCH_POWER_H
#define SAP_WATCH_POWER_H

int   power_init(void);
void  power_update(void);
float power_get_battery_pct(void);
float power_get_battery_v(void);
float power_get_solar_v(void);
int   power_is_charging(void);
int   power_is_low(void);
int   power_is_critical(void);
int   power_should_deep_sleep(void);
void  power_enter_deep_sleep(void);
int   power_in_deep_sleep(void);
int   power_can_fire_heater(void);

#endif /* SAP_WATCH_POWER_H */