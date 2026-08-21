/*
 * volt-scribe — display.h
 * SSD1306 OLED display interface
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include "stm32g4xx_hal.h"

void display_init(void);
void display_clear(void);
void display_pixel(int x, int y, int set);
void display_line(int x0, int y0, int x1, int y1);
void display_update(void);

void display_show_splash(void);
void display_show_idle(void);
void display_show_running(int mode);
void display_show_mode(int mode);

void display_plot_cv(const float *E, const float *I, int n,
                     const void *peaks, int n_peaks);
void display_plot_dpv(const float *E, const float *dI, int n);
void display_plot_swv(const float *E, const float *dI, int n);
void display_plot_nyquist(const void *eis_data, int n);
void display_plot_it(float t, float I);

#endif /* DISPLAY_H */