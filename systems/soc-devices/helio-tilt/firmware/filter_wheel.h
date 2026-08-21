/*
 * filter_wheel.h — 6-position filter wheel (SG90 servo)
 */

#ifndef FILTER_WHEEL_H
#define FILTER_WHEEL_H

#include <stdint.h>

/* Initialize servo PWM (TIM4_CH1, 50 Hz) */
void filter_wheel_init(void);

/* Move to position 0–5 (405/440/675/870/940/1640 nm) */
void filter_wheel_set(uint8_t position);

/* Get current position (0–5) */
uint8_t filter_wheel_get(void);

/* Home the filter wheel using optical slot sensor */
int filter_wheel_home(void);

#endif /* FILTER_WHEEL_H */