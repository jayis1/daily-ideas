/*
 * Spectra Charm — led_indicator.h
 */
#ifndef LED_INDICATOR_H
#define LED_INDICATOR_H

typedef enum {
    LED_COLOR_OFF = 0,
    LED_COLOR_RED,
    LED_COLOR_GREEN,
    LED_COLOR_BLUE,
    LED_COLOR_CYAN,
    LED_COLOR_YELLOW,
    LED_COLOR_WHITE,
} LEDColor_t;

void LED_Init(int gpio);
void LED_SetColor(LEDColor_t color);
void LED_Update(void);

#endif