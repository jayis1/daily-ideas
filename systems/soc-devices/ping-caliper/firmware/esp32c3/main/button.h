/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/button.h — Trigger + user buttons
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef BUTTON_H
#define BUTTON_H

#include <stdint.h>

void button_init(void);

/* Returns 1 if the trigger button was pressed since last call. */
uint8_t button_trigger_pressed(void);

/* Returns 1 if the menu button was pressed. */
uint8_t button_menu_pressed(void);

/* Returns 1 if the mode button was pressed. */
uint8_t button_mode_pressed(void);

#endif /* BUTTON_H */