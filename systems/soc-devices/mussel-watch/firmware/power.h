/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * power.h — Battery/solar monitoring, sleep management
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef POWER_H
#define POWER_H

#include "config.h"

/* Initialize the SAADC for battery and solar voltage monitoring */
int power_init(void);

/* Read battery voltage (returns volts) */
float power_read_battery_v(void);

/* Read solar panel voltage (returns volts) */
float power_read_solar_v(void);

/* Compute battery percentage from voltage (0–100%) */
int power_battery_pct(float voltage);

/* Check if the solar panel is actively charging */
int power_is_charging(float solar_v);

/* Enter low-power sleep mode for `ms` milliseconds.
 * Powers down sensors, radio, and SD card; wakes on RTC or GPIO. */
void power_enter_sleep(uint32_t ms);

/* Full power management: read voltages, update state, handle low battery */
void power_manage(mussel_watch_state_t *st);

#endif /* POWER_H */