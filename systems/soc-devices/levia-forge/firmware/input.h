/*
 * Levia Forge — Input Header
 * SPDX-License-Identifier: MIT
 */
#ifndef INPUT_H
#define INPUT_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    float x;  /* -1.0 to +1.0 */
    float y;  /* -1.0 to +1.0 */
} input_joystick_t;

void input_init(void);
input_joystick_t input_read_joystick(void);
float input_read_encoder_delta(void);
bool input_read_button(uint8_t pin);
int input_read_battery_mv(void);
float input_read_temp_c(void);
void input_set_led(bool on);

#endif /* INPUT_H */