/*
 * ui.h — Button debouncing and menu navigation (header)
 */
#ifndef UI_H
#define UI_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    UI_IDLE,
    UI_SET_MASS,
    UI_SET_RAMP,
    UI_HEATING,
    UI_COOLDOWN,
    UI_ABORT,
    UI_MATCH,
} ui_state_t;

void    ui_init(void);
bool    ui_button_a(void);  /* START/STOP/SELECT */
bool    ui_button_b(void);  /* UP/NEXT */
bool    ui_button_c(void);  /* DOWN/SELECT */
void    ui_poll(void);
void    ui_led_red(bool on);
void    ui_led_green(bool on);
float   ui_get_mass(void);
float   ui_get_ramp(void);
void    ui_set_mass(float m);
void    ui_set_ramp(float r);

#endif /* UI_H */