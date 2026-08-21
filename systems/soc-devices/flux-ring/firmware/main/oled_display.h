/*
 * Flux Ring — oled_display.h
 * SSD1306 32x64 monochrome OLED display driver.
 * I2C address: 0x3C
 */

#ifndef OLED_DISPLAY_H_
#define OLED_DISPLAY_H_

#include "field_engine.h"
#include "compass.h"
#include <stdint.h>

/* Operating modes (for display context) */
typedef enum {
    DISP_MODE_MONITOR = 0,
    DISP_MODE_EXPLORE = 1,
    DISP_MODE_MAPPING = 2,
    DISP_MODE_COMPASS = 3,
} disp_mode_t;

/**
 * Initialize SSD1306 OLED over I2C.
 * Sets up 32x64 display mode.
 */
int oled_display_init(void);

/**
 * Update display with current field data.
 * Layout depends on current mode.
 */
void oled_display_update(const field_vector_t *field, float magnitude,
                         compass_heading_t heading, pole_t pole,
                         disp_mode_t mode, uint8_t battery_pct);

/**
 * Show "CALIBRATING..." message.
 */
void oled_display_calibrating(void);

/**
 * Show "CAL OK" message.
 */
void oled_display_cal_ok(void);

/**
 * Turn off display (sleep mode).
 */
void oled_display_off(void);

/**
 * Turn on display (wake from sleep).
 */
void oled_display_on(void);

#endif /* OLED_DISPLAY_H_ */