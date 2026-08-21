/*
 * pyro-balance / Core/Inc/oled_display.h
 */
#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H
#include "main.h"
void oled_init(void);
void oled_clear(void);
void oled_draw_tg(const tga_run_t* run, float cur_temp, float cur_mass_pct);
void oled_status(const pb_status_t* s);
void oled_text(uint8_t line, const char* s);
void oled_invert(bool on);
#endif