/*
 * dent-scope / Core/Inc/oled_display.h
 * Dent Scope — SSD1306 OLED display driver
 * MIT License.
 */
#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H

#include "main.h"

void oled_init(void);
void oled_text(uint8_t row, const char *txt);
void oled_draw_status(ds_status_t *st);
void oled_draw_results(ds_status_t *st);
void oled_draw_ph_curve(ds_status_t *st);

#endif /* OLED_DISPLAY_H */