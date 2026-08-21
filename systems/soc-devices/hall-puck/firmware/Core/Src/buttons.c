/*
 * hall-puck / firmware / Core / Src / buttons.c
 * Debounced button input
 *
 * MIT License.
 */
#include "buttons.h"
#include "main.h"

#define DEBOUNCE_MS     20
#define LONG_PRESS_MS   1000

typedef struct {
    uint8_t pin;
    bool pressed;
    bool long_sent;
    uint32_t press_time;
    uint32_t last_debounce;
} button_state_t;

static button_state_t buttons[3];

void buttons_init(void)
{
    /* Configure button pins as input with pull-up */
    /* PC8, PC9, PC10 */
    GPIOC->MODER &= ~(3 << (BTN_MEASURE_PIN * 2) |
                      3 << (BTN_MODE_PIN * 2) |
                      3 << (BTN_MENU_PIN * 2));
    /* Enable pull-up on all 3 buttons */
    GPIOC->PUPDR &= ~(3 << (BTN_MEASURE_PIN * 2) |
                      3 << (BTN_MODE_PIN * 2) |
                      3 << (BTN_MENU_PIN * 2));
    GPIOC->PUPDR |= (1 << (BTN_MEASURE_PIN * 2) |
                     1 << (BTN_MODE_PIN * 2) |
                     1 << (BTN_MENU_PIN * 2));

    buttons[0].pin = BTN_MEASURE_PIN;
    buttons[1].pin = BTN_MODE_PIN;
    buttons[2].pin = BTN_MENU_PIN;

    for (int i = 0; i < 3; i++) {
        buttons[i].pressed = false;
        buttons[i].long_sent = false;
        buttons[i].press_time = 0;
        buttons[i].last_debounce = 0;
    }
}

static bool read_pin(uint8_t pin)
{
    /* Active low (pull-up + button to GND) */
    if (pin < 16) return !(GPIOA->IDR & (1 << pin));
    else return !(GPIOC->IDR & (1 << (pin - 16)));
    /* Actually PC8-PC10 are on GPIOC */
}

static bool read_button_pin(uint8_t pin)
{
    return !(GPIOC->IDR & (1 << pin));
}

button_event_t buttons_poll(void)
{
    uint32_t now = sys_tick_ms;

    for (int i = 0; i < 3; i++) {
        bool raw = read_button_pin(buttons[i].pin);

        if (raw != buttons[i].pressed) {
            /* State change — check debounce */
            if ((now - buttons[i].last_debounce) > DEBOUNCE_MS) {
                buttons[i].pressed = raw;
                buttons[i].last_debounce = now;

                if (raw) {
                    /* Button just pressed */
                    buttons[i].press_time = now;
                    buttons[i].long_sent = false;
                } else {
                    /* Button just released */
                    if (!buttons[i].long_sent) {
                        /* Short press event */
                        switch (i) {
                        case 0: return BTN_MEASURE_PRESS;
                        case 1: return BTN_MODE_PRESS;
                        case 2: return BTN_MENU_PRESS;
                        }
                    }
                }
            }
        }

        /* Check for long press (button still held) */
        if (buttons[i].pressed && !buttons[i].long_sent) {
            if ((now - buttons[i].press_time) > LONG_PRESS_MS) {
                buttons[i].long_sent = true;
                if (i == 0) return BTN_MEASURE_LONG;
            }
        }
    }

    return BTN_NONE;
}

button_event_t buttons_wait(int timeout_ms)
{
    uint32_t start = sys_tick_ms;
    while ((int32_t)(sys_tick_ms - start) < timeout_ms) {
        button_event_t ev = buttons_poll();
        if (ev != BTN_NONE) return ev;
        delay_ms(5);
    }
    return BTN_NONE;
}