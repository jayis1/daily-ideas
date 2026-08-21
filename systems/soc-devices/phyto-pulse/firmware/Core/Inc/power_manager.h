/*
 * power_manager.h — Power state management
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    PWR_STOP = 0,
    PWR_IDLE,
    PWR_RECORDING,
    PWR_STREAMING,
} power_state_t;

void power_manager_init(void);
void power_manager_set_state(power_state_t state);
power_state_t power_manager_get_state(void);
float power_manager_get_battery_voltage(void);
bool power_manager_is_charging(void);
uint8_t power_manager_get_battery_pct(void);

/* Enter STOP mode (deep sleep, RTC wakeup) */
void power_manager_enter_stop(void);

#endif /* POWER_MANAGER_H */