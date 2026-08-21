/*
 * Pulse Hound — RF Signal Hunter
 * display.h — OLED display interface
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef PULSE_HOUND_DISPLAY_H
#define PULSE_HOUND_DISPLAY_H

#include "config.h"

void display_init(void);
void display_off(void);
void display_on(void);

void display_clear(void);
void display_set_pixel(int x, int y, int on);
void display_draw_char(int x, int y, char c);
void display_draw_text(int x, int y, const char *text);
void display_draw_text_p(int x, int y, const char *text);

void display_render(float rssi_dbm, float peak_rssi, signal_class_t cls,
                    float bearing_deg, int battery_pct,
                    pulse_hound_mode_t mode, int audio_on);
void display_flush(void);

#endif /* PULSE_HOUND_DISPLAY_H */