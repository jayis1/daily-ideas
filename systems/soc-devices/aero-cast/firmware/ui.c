/* ui.c — button handling and mode state machine */

#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "ui.h"
#include "sdkconfig.h"

static ui_mode_t current_mode = UI_MODE_WIND;
static ui_avg_window_t avg_window = AVG_1S;

static uint32_t btn_press_time[3] = {0, 0, 0};
static bool btn_was_pressed[3] = {false, false, false};

static const uint8_t btn_pins[3] = { PIN_BTN_PWR, PIN_BTN_MODE, PIN_BTN_AVG };

static void debounced_poll(int idx)
{
    bool pressed = (gpio_get(btn_pins[idx]) == 0);  /* active low */
    uint32_t now = time_us_32();

    if (pressed && !btn_was_pressed[idx]) {
        /* Button just pressed (falling edge) */
        btn_press_time[idx] = now;
        btn_was_pressed[idx] = true;

        switch (idx) {
        case 0:  /* PWR button — handled in power_held check */
            break;
        case 1:  /* MODE */
            ui_next_mode();
            break;
        case 2:  /* AVG */
            ui_next_avg();
            break;
        }
    } else if (!pressed && btn_was_pressed[idx]) {
        /* Button released */
        btn_was_pressed[idx] = false;
    }
}

void ui_init(void)
{
    for (int i = 0; i < 3; i++) {
        gpio_init(btn_pins[i]);
        gpio_set_dir(btn_pins[i], GPIO_IN);
        gpio_pull_up(btn_pins[i]);
        btn_was_pressed[i] = false;
        btn_press_time[i] = 0;
    }
    printf("[ui] buttons initialized\n");
}

void ui_poll(void)
{
    for (int i = 0; i < 3; i++) {
        debounced_poll(i);
        sleep_us(100);  /* tiny settle between reads */
    }
}

ui_mode_t ui_get_mode(void) { return current_mode; }

ui_avg_window_t ui_get_avg_window(void) { return avg_window; }

uint32_t ui_avg_seconds(void)
{
    switch (avg_window) {
    case AVG_1S:    return 1;
    case AVG_10S:   return 10;
    case AVG_1MIN:  return 60;
    case AVG_10MIN: return 600;
    case AVG_30MIN: return 1800;
    default:        return 1;
    }
}

void ui_next_mode(void)
{
    current_mode = (ui_mode_t)((current_mode + 1) % UI_MODE_NUM);
    printf("[ui] mode = %d\n", current_mode);
}

void ui_next_avg(void)
{
    avg_window = (ui_avg_window_t)((avg_window + 1) % AVG_NUM);
    printf("[ui] avg window = %d (%lu s)\n", avg_window, ui_avg_seconds());
}

bool ui_power_held(void)
{
    /* If PWR button held for >2 seconds, request shutdown */
    if (btn_was_pressed[0]) {
        uint32_t held_us = time_us_32() - btn_press_time[0];
        if (held_us > 2000000)
            return true;
    }
    return false;
}