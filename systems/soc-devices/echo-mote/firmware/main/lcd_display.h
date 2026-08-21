/**
 * lcd_display.h — ST7789V 1.3" IPS LCD driver (240×240, SPI)
 */

#ifndef LCD_DISPLAY_H
#define LCD_DISPLAY_H

#include <stdint.h>
#include "acoustic_params.h"

/* Measurement modes (must match app_main.c) */
typedef enum {
    LCD_MODE_RT60 = 0,
    LCD_MODE_FREQ,
    LCD_MODE_ROOM_MODES,
    LCD_MODE_CLARITY,
    LCD_MODE_NOISE,
} lcd_mode_t;

/**
 * Initialize the ST7789V LCD via SPI.
 * Configures GPIO for DC, CS, RST, backlight.
 */
int lcd_display_init(void);

/**
 * Show mode selection screen.
 */
void lcd_display_mode_select(uint32_t mode);

/**
 * Show measurement in progress screen.
 *
 * @param mode     Current measurement mode
 * @param progress Progress percentage (0–100)
 */
void lcd_display_measuring(uint32_t mode, uint32_t progress);

/**
 * Show measurement results on the LCD.
 *
 * @param mode    Measurement mode that produced results
 * @param results Acoustic results to display
 */
void lcd_display_results(uint32_t mode, const acoustic_results_t *results);

/**
 * Show idle screen with battery, temperature, humidity.
 */
void lcd_display_idle(uint32_t mode, float battery_v, float temp, float humidity);

/**
 * Turn off the LCD backlight and display.
 */
void lcd_display_off(void);

#endif /* LCD_DISPLAY_H */