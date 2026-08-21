/*
 * power.h — Battery/solar monitoring, fuel gauge, charge LED, light sleep
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_POWER_H
#define ECHO_TRAP_POWER_H

#include <stdint.h>

void power_init(void);
void power_update(uint8_t *battery_pct, float *temp_c,
                  float *humidity_pct, float *light_lux);
void power_update_charge_led(void);
void power_low_battery_handler(void);

#endif /* ECHO_TRAP_POWER_H */