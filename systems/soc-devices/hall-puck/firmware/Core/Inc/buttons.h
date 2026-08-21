/*
 * hall-puck / firmware / Core / Inc / buttons.h
 * Debounced button input
 *
 * MIT License.
 */
#ifndef BUTTONS_H
#define BUTTONS_H

#include <stdbool.h>

typedef enum {
    BTN_NONE = 0,
    BTN_MEASURE_PRESS,
    BTN_MEASURE_LONG,
    BTN_MODE_PRESS,
    BTN_MENU_PRESS,
} button_event_t;

void buttons_init(void);
button_event_t buttons_poll(void);
button_event_t buttons_wait(int timeout_ms);

#endif /* BUTTONS_H */