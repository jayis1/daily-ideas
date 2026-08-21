/*
 * display.h — OLED SH1106 rendering
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include "config.h"

void display_init(void);
void display_clear(void);
void display_update(void);

/* Screens */
void display_boot(const char *msg);
void display_idle(float temp, float vbat, uint8_t channel);
void display_menu(uint8_t item);
void display_measure_live(const qcm_result_t *r, float elapsed_s);
void display_dissipation_plot(const uint16_t *samples, uint16_t n, float D);
void display_result(const qcm_result_t *r);
void display_overtone_table(const overtone_sweep_t *s);
void display_voigt_result(const voigt_params_t *v);
void display_error(const char *msg);
void display_status_bar(float temp, float vbat, const char *state);

/* Low-level */
void display_set_cursor(uint8_t x, uint8_t y);
void display_text(uint8_t x, uint8_t y, const char *str, uint8_t size);
void display_pixel(uint8_t x, uint8_t y, uint8_t on);
void display_line(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1);
void display_hline(uint8_t x, uint8_t y, uint8_t w);
void display_vline(uint8_t x, uint8_t y, uint8_t h);
void display_rect(uint8_t x, uint8_t y, uint8_t w, uint8_t h);
void display_plot_df_dd(float *df, float *dd, uint16_t n, uint16_t current);

#endif /* DISPLAY_H */