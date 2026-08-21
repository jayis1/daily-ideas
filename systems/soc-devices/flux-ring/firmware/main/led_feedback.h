/*
 * Flux Ring — led_feedback.h
 * WS2812B RGB LED feedback for field strength visualization.
 */

#ifndef LED_FEEDBACK_H_
#define LED_FEEDBACK_H_

#include <stdint.h>
#include "field_engine.h"

/**
 * Initialize WS2812B LED on GPIO.
 */
int led_feedback_init(void);

/**
 * Set LED color based on field magnitude and dominant pole.
 * Color map:
 *   0-0.5G   → soft blue (ambient Earth field)
 *   0.5-1G   → cyan
 *   1-3G     → green
 *   3-10G    → yellow
 *   10-50G   → orange
 *   50-800G  → red (near magnet)
 *
 * N-pole dominant → warm tint
 * S-pole dominant → cool tint
 */
void led_feedback_set_field(float magnitude_gauss, pole_t pole);

/**
 * Turn off the LED.
 */
void led_feedback_off(void);

#endif /* LED_FEEDBACK_H_ */