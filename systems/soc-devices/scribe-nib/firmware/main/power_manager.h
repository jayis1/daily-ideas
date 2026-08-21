/*
 * power_manager.h — Power state management API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <stdint.h>

typedef enum {
    POWER_STATE_ACTIVE      = 0,  /* Full speed, all peripherals on */
    POWER_STATE_IDLE        = 1,  /* IMU low-ODR, BLE connected, OLED off */
    POWER_STATE_LIGHT_SLEEP = 2,  /* IMU 1Hz, BLE advertising only */
    POWER_STATE_DEEP_SLEEP  = 3,  /* ULP + RTC only, ~8µA */
} power_state_t;

/**
 * @brief Initialize power manager.
 */
void power_manager_init(void);

/**
 * @brief Call periodically to check inactivity and transition states.
 */
void power_manager_update(void);

/**
 * @brief Force transition to a new power state.
 */
void power_manager_transition(power_state_t new_state);

/**
 * @brief Wake from any sleep state to ACTIVE.
 */
void power_manager_wake(void);

/**
 * @brief Record activity (resets inactivity timer).
 */
void power_manager_activity(void);

/**
 * @brief Get current power state.
 */
power_state_t power_manager_get_state(void);

#endif /* POWER_MANAGER_H */