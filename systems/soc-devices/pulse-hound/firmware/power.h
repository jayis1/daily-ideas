/*
 * Pulse Hound — RF Signal Hunter
 * power.h — Power management interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_POWER_H
#define PULSE_HOUND_POWER_H

int  power_init(void);
void power_update(void);
int  power_get_battery_pct(void);
int  power_is_charging(void);
int  power_is_low_power(void);
int  power_can_sustain_sweep(void);
int  power_can_sustain_df(void);
float power_get_voltage(void);
void power_enter_deep_sleep(void);
void power_exit_deep_sleep(void);

#endif /* PULSE_HOUND_POWER_H */