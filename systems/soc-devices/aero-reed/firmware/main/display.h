/*
 * display.h — SSD1306 OLED rendering
 */
#pragma once
#include "synth.h"

void display_init(void);
void display_update(const aero_state_t *st);