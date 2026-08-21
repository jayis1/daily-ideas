/*
 * led.h — RGB status LED driver
 * Opti Rot — Pocket Digital Polarimeter
 */
#ifndef LED_H
#define LED_H

#include <stdint.h>

#define LED_COLOR_OFF    0
#define LED_COLOR_RED    1
#define LED_COLOR_GREEN  2
#define LED_COLOR_BLUE   3
#define LED_COLOR_YELLOW 4
#define LED_COLOR_CYAN   5
#define LED_COLOR_MAGENTA 6
#define LED_COLOR_WHITE  7

void led_init(void);
void led_set_color(uint8_t color, uint8_t brightness);  /* brightness 0-255 */

#endif /* LED_H */