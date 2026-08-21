/*
 * visco-shear / firmware / oled_display.h
 */
#ifndef VISCO_SHEAR_OLED_H
#define VISCO_SHEAR_OLED_H

#include "main.h"

void oled_display_init(void);
void oled_display_show_idle(measure_mode_t mode, spindle_type_t sp, float temp, float vbat);
void oled_display_show_status(const char *line1, const char *line2);
void oled_display_show_flow_point(int step, int total, float eta, float gamma);
void oled_display_show_osc_point(int step, int total, float Gp, float Gd);
void oled_display_show_result(const measure_result_t *res);

#endif