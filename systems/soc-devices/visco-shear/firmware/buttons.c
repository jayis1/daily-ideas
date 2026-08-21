/*
 * visco-shear / firmware / buttons.c
 * Debounced button input (3 tactile buttons: START, MODE, MENU)
 *
 * MIT License.
 */
#include "pico/stdlib.h"
#include "main.h"
#include "buttons.h"

void buttons_init(void)
{
    const int pins[] = { PIN_BTN_START, PIN_BTN_MODE, PIN_BTN_MENU };
    for (int i = 0; i < 3; i++) {
        gpio_init(pins[i]);
        gpio_set_dir(pins[i], GPIO_IN);
        gpio_pull_up(pins[i]);  /* Active low with pull-up */
    }
    printf("[BTN] Buttons initialized (START=%d, MODE=%d, MENU=%d)\n",
           PIN_BTN_START, PIN_BTN_MODE, PIN_BTN_MENU);
}

bool button_is_pressed(int pin)
{
    return gpio_get(pin) == 0;
}