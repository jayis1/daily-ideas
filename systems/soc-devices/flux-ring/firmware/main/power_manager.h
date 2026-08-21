/*
 * Flux Ring — power_manager.h
 * Power management, battery monitoring, and sleep modes.
 */

#ifndef POWER_MANAGER_H_
#define POWER_MANAGER_H_

#include <stdint.h>

/**
 * Initialize power manager.
 * Configures ADC for battery voltage reading.
 */
int power_manager_init(void);

/**
 * Get battery level as percentage (0-100).
 * Reads battery voltage through a 1:2 voltage divider on ADC.
 */
uint8_t power_manager_battery_pct(void);

/**
 * Get battery voltage in millivolts.
 */
uint16_t power_manager_battery_mv(void);

/**
 * Enter deep sleep until next wake event.
 * Configures wake-on-motion interrupt from accelerometer.
 */
void power_manager_deep_sleep(void);

/**
 * Idle power management (light sleep with fast wake).
 */
void power_manager_idle(void);

/**
 * Check if USB power is present (charging).
 */
bool power_manager_usb_connected(void);

#endif /* POWER_MANAGER_H_ */