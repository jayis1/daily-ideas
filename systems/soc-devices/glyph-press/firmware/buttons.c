/**
 * glyph_press/firmware/buttons.c — Debounced Button Polling
 */

#include "main.h"
#include "pico/stdlib.h"
#include "hardware/gpio.h"

static uint8_t s_debounce[3] = {0};
static bool    s_pressed[3]  = {false};

void buttons_init(void)
{
    const uint8_t pins[3] = {PIN_BTN_START, PIN_BTN_MODE, PIN_BTN_FEED};
    for (int i = 0; i < 3; i++) {
        gpio_init(pins[i]);
        gpio_set_dir(pins[i], GPIO_IN);
        gpio_pull_up(pins[i]);
    }
}

void buttons_poll(void)
{
    const uint8_t pins[3] = {PIN_BTN_START, PIN_BTN_MODE, PIN_BTN_FEED};
    for (int i = 0; i < 3; i++) {
        bool raw = (gpio_get(pins[i]) == 0);
        s_debounce[i] = (uint8_t)((s_debounce[i] << 1) | (raw ? 1 : 0));
        if (s_debounce[i] == 0xFF)
            s_pressed[i] = true;
        else if (s_debounce[i] == 0x00)
            s_pressed[i] = false;
    }
}

bool button_start_pressed(void) { bool p = s_pressed[0]; s_pressed[0] = false; return p; }
bool button_mode_pressed(void)  { bool p = s_pressed[1]; s_pressed[1] = false; return p; }
bool button_feed_pressed(void)  { bool p = s_pressed[2]; s_pressed[2] = false; return p; }