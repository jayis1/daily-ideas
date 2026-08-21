/*
 * Tremor Tile — Status LED Header
 * status_led.h
 */

#ifndef TREMOR_TILE_STATUS_LED_H
#define TREMOR_TILE_STATUS_LED_H

#include "config.h"

void status_led_init(void);
void status_led_set(uint8_t pattern);

#endif // TREMOR_TILE_STATUS_LED_H