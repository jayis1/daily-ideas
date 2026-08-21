/*
 * Flux Ring — touch_input.h
 * Capacitive touch input for mode cycling.
 */

#ifndef TOUCH_INPUT_H_
#define TOUCH_INPUT_H_

#include <stdint.h>

/**
 * Initialize capacitive touch sensor on GPIO.
 * @param single_tap_cb   Callback for single tap (mode cycle)
 * @param double_tap_cb   Callback for double tap (toggle mapping)
 */
int touch_input_init(void (*single_tap_cb)(void),
                     void (*double_tap_cb)(void));

/**
 * Poll touch sensor (call from main loop or timer).
 * Handles debouncing and double-tap detection.
 */
void touch_input_poll(void);

#endif /* TOUCH_INPUT_H_ */