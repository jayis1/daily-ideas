/*
 * kappa-pin / firmware / main / buttons.h
 * Debounced button input
 *
 * MIT License.
 */
#ifndef BUTTONS_H
#define BUTTONS_H

#include <stdbool.h>

/* Button pins */
#define BTN_MEASURE_PIN  14
#define BTN_MODE_PIN     15
#define BTN_MENU_PIN     16

typedef enum {
    BTN_NONE = 0,
    BTN_MEASURE_PRESS,
    BTN_MEASURE_LONG,
    BTN_MODE_PRESS,
    BTN_MENU_PRESS,
} button_event_t;

/* Initialize button GPIOs with debouncing */
void buttons_init(void);

/* Poll for button event (non-blocking) */
button_event_t buttons_poll(void);

/* Wait for button event (blocking, with timeout ms) */
button_event_t buttons_wait(int timeout_ms);

#endif /* BUTTONS_H */