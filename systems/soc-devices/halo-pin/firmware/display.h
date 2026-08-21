/*
 * display.h — SH1106 OLED display for particle counter
 *
 * Shows histogram of 16 size bins, PM1/PM2.5/PM10, flow rate, battery,
 * calibration progress, and menu navigation.
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>
#include "ui.h"

void   display_init(void);
void   display_show_message(const char *line1, const char *line2);
void   display_show_menu(ui_menu_t item);
void   display_show_sampling(const uint32_t *counts, uint8_t n,
                              float flow_lpm, float pm25, float pm10,
                              float battery_v);
void   display_show_calibration(const uint32_t *counts, float size_um);
void   display_show_results(float pm1, float pm25, float pm10,
                             float flow, const uint32_t *counts, uint8_t n);
void   display_clear(void);

#endif /* DISPLAY_H */