/**
 * power_manager.h — Low-power management and battery monitoring
 */
#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include "stm32g4xx_hal.h"
#include <stdint.h>

void power_manager_init(void);
void power_manager_enter_stop(void);
uint8_t power_manager_read_battery(void);
uint8_t power_manager_is_charging(void);

#endif /* POWER_MANAGER_H */