/*
 * Tremor Tile — Power Manager Header
 * power_manager.h
 */

#ifndef TREMOR_TILE_POWER_MANAGER_H
#define TREMOR_TILE_POWER_MANAGER_H

void power_manager_init(void);
float power_manager_read_battery_pct(void);
float power_manager_read_solar_voltage(void);
void power_manager_sleep_until_next_event(void);

#endif // TREMOR_TILE_POWER_MANAGER_H