/**
 * power_manager.h — Power management: battery monitoring, deep sleep, charge status
 */

#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

/**
 * Initialize power manager.
 * Configures ADC for battery voltage sensing and charge status GPIO.
 */
int power_manager_init(void);

/**
 * Read battery voltage.
 *
 * @return Battery voltage in volts (e.g., 3.85)
 */
float power_manager_read_battery(void);

/**
 * Store speaker SPL calibration offset in NVS.
 */
void power_manager_cal_spl(float db_offset);

/**
 * Get speaker SPL calibration offset from NVS.
 */
float power_manager_get_spl_offset(void);

#endif /* POWER_MANAGER_H */