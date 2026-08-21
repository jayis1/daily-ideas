/*
 * Phase Scope — Display driver header
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>
#include "power_quality.h"

void display_init(void);
void display_clear(void);
void display_update(void);
void display_set_pixel(int x, int y, int set);
void display_draw_line(int x0, int y0, int x1, int y1);
void display_draw_rect(int x, int y, int w, int h);
void display_fill_rect(int x, int y, int w, int h);
void display_draw_circle(int cx, int cy, int r);
void display_draw_char(int x, int y, char c, int font);
void display_draw_string(int x, int y, const char *str, int font);
void display_render_page(uint8_t page, const power_results_t *res);

/* Individual page renderers */
static void render_phasor(const power_results_t *res);
static void render_waveform(const power_results_t *res);
static void render_harmonics(const power_results_t *res);
static void render_numeric(const power_results_t *res);
static void render_transient(const power_results_t *res);

#endif /* DISPLAY_H */