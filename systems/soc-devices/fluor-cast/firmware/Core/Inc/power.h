/*
 * power.h — Battery management and power monitoring
 */

#ifndef POWER_H
#define POWER_H

#include <stdint.h>

/**
 * Initialize power management ADC.
 */
void power_init(void);

/**
 * Read battery voltage.
 * @return Voltage in volts
 */
float power_battery_voltage(void);

/**
 * Read battery current.
 * @return Current in mA (positive=charging, negative=discharging)
 */
float power_battery_current(void);

/**
 * Get battery percentage (0–100).
 */
uint8_t power_battery_pct(void);

/**
 * Check if USB charger is connected.
 * @return 1 if charging, 0 if not
 */
int power_is_charging(void);

/**
 * Enter low-power mode (stop most peripherals).
 */
void power_low_power(void);

/**
 * Wake from low-power mode.
 */
void power_wake(void);

/**
 * Check if battery is low.
 * @return 1 if battery < 20%, 0 if OK
 */
int power_battery_low(void);

/**
 * Estimate remaining runtime in minutes.
 */
uint16_t power_remaining_minutes(void);

#endif /* POWER_H */