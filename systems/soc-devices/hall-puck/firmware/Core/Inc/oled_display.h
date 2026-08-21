/*
 * hall-puck / firmware / Core / Inc / oled_display.h
 * SSD1306 OLED 128x64 display driver (SPI)
 *
 * MIT License.
 */
#ifndef OLED_DISPLAY_H
#define OLED_DISPLAY_H

#include <stdbool.h>
#include "measurement.h"

void oled_init(void);
void oled_show_idle(float temp_c, const meas_params_t *params);
void oled_show_contact_check(int contact, bool ok);
void oled_show_vdp_progress(float ra, float rb, float rs);
void oled_show_hall_progress(const char *phase, float voltage_uv, float b_field);
void oled_show_result(const meas_result_t *r);
void oled_show_menu(int item, const char **items, int n_items);
void oled_clear(void);

#endif /* OLED_DISPLAY_H */