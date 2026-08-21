/*
 * cor-sono / firmware / oled_display.h
 */
#pragma once
#include "main.h"

void oled_init(void);
void oled_clear(void);
void oled_flush(void);
void oled_draw_text(int x, int y, const char *str, int size);
void oled_draw_waveform(const int16_t *audio, int n, int y_start, int height);
void oled_update_status(int hr, int class_id, int confidence);
void oled_show_idle(void);