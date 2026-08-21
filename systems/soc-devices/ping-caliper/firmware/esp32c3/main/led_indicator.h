/*
 * Ping Caliper — ESP32-C3 Communications Module
 * main/led_indicator.h — Status LED driver (RGB via single WS2812 or 3 LEDs)
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef LED_INDICATOR_H
#define LED_INDICATOR_H

#include <stdint.h>

typedef enum {
    LED_RED,
    LED_GREEN,
    LED_BLUE,
} led_t;

typedef enum {
    LED_OFF,
    LED_ON,
    LED_BLINK,
    LED_BLINK_FAST,
} led_state_t;

void led_indicator_init(void);
void led_indicator_set(led_t led, led_state_t state);

#endif /* LED_INDICATOR_H */