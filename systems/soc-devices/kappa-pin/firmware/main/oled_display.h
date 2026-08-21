/*
 * kappa-pin / firmware / main / oled_display.h
 * SSD1306 OLED 128x64 display driver (SPI)
 *
 * MIT License.
 */
#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H

#include <stdbool.h>
#include "measurement.h"

/* OLED pins */
#define OLED_CS_PIN     9
#define OLED_DC_PIN     10
#define OLED_RES_PIN    11
/* Shared SPI: SCK=5, MOSI=7 */

typedef enum {
    OLED_SCREEN_IDLE = 0,
    OLED_SCREEN_ARMING,
    OLED_SCREEN_MEASURING,
    OLED_SCREEN_RESULT,
    OLED_SCREEN_MENU,
} oled_screen_t;

void oled_init(void);
void oled_show_idle(float temp_c, material_t mat, const char *probe_name);
void oled_show_arming(float temp_c, float drift, bool ready);
void oled_show_measuring(float t_elapsed, float dt_mk, float q_w, float target_q);
void oled_show_result(const meas_result_t *r);
void oled_show_menu(int item, const char **items, int n_items);
void oled_clear(void);
void oled_draw_dt_curve(const meas_sample_t *samples, int count, int window_start);
void oled_draw_ln_t_fit(const meas_sample_t *samples, int count,
                         int fit_start, int fit_end, float slope, float intercept);

#endif /* OLED_DISPLAY_H */