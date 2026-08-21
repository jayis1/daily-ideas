/**
 * glyph_press/firmware/encoder.c — Rotary Encoder Reader
 *
 * EC11 rotary encoder on GP17 (A) / GP18 (B).
 * Returns delta: -1, 0, or +1 per call.
 * Uses a simple state-machine decode based on previous A/B state.
 */

#include "main.h"
#include "pico/stdlib.h"
#include "hardware/gpio.h"

static uint8_t s_prev_state = 0;
static int8_t  s_delta = 0;

void encoder_init(void)
{
    gpio_init(PIN_ENC_A);
    gpio_set_dir(PIN_ENC_A, GPIO_IN);
    gpio_pull_up(PIN_ENC_A);

    gpio_init(PIN_ENC_B);
    gpio_set_dir(PIN_ENC_B, GPIO_IN);
    gpio_pull_up(PIN_ENC_B);

    s_prev_state = (gpio_get(PIN_ENC_A) << 1) | gpio_get(PIN_ENC_B);
}

int8_t encoder_delta(void)
{
    uint8_t a = gpio_get(PIN_ENC_A) ? 1 : 0;
    uint8_t b = gpio_get(PIN_ENC_B) ? 1 : 0;
    uint8_t state = (a << 1) | b;

    /* Gray code transition table */
    static const int8_t transitions[4][4] = {
        /* prev=00 */ { 0,  1, -1,  0},
        /* prev=01 */ {-1,  0,  0,  1},
        /* prev=10 */ { 1,  0,  0, -1},
        /* prev=11 */ { 0, -1,  1,  0}
    };

    int8_t d = transitions[s_prev_state & 3][state & 3];
    s_delta += d;
    s_prev_state = state;

    int8_t result = 0;
    if (s_delta >= 4) { result = 1;  s_delta -= 4; }
    else if (s_delta <= -4) { result = -1; s_delta += 4; }
    return result;
}