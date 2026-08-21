/*
 * oled_display.h — SSD1306 64×32 OLED display API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H

#include "esp_err.h"
#include <stdarg.h>

/**
 * @brief Initialize SSD1306 64×32 OLED over I²C.
 */
esp_err_t oled_display_init(void);

/**
 * @brief Clear the display framebuffer.
 */
esp_err_t oled_display_clear(void);

/**
 * @brief Flush framebuffer to display.
 */
esp_err_t oled_display_flush(void);

/**
 * @brief Display a single character (large, centered).
 */
esp_err_t oled_display_char(char c);

/**
 * @brief Display a glyph (alias for oled_display_char).
 */
esp_err_t oled_display_glyph(char c);

/**
 * @brief Display formatted text (small font, top-left).
 */
esp_err_t oled_display_printf(const char *fmt, ...);

/**
 * @brief Turn display off (sleep mode).
 */
esp_err_t oled_display_off(void);

/**
 * @brief Turn display on.
 */
esp_err_t oled_display_on(void);

#endif /* OLED_DISPLAY_H */