/*
 * Hive Mind — Power Manager Header
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <stdint.h>

void power_manager_init(void);
float power_manager_read_battery(void);
float power_manager_read_solar(void);
void power_manager_enter_stop(void);
void power_manager_enter_standby(void);
uint8_t power_manager_user_button_pressed(void);

#endif /* POWER_MANAGER_H */