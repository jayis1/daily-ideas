/*
 * display.h — SH1106 OLED driver (header)
 */
#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>

void display_init(void);
void display_clear(void);
void display_update(void);
void display_set_pixel(int16_t x, int16_t y, uint8_t val);
void display_draw_hline(int16_t x, int16_t y, int16_t w);
void display_draw_vline(int16_t x, int16_t y, int16_t h);
void display_text(int16_t x, int16_t y, const char *str);
void display_status(float temp, float setpoint, float heat_flow, float ramp_rate, uint8_t battery);
void display_dsc_curve(const float *temp_data, const float *hf_data, uint32_t count, uint32_t max_points);
void display_peak_markers(int16_t *peak_indices, uint8_t num_peaks, uint32_t max_points);
void display_match(const char *name, float confidence);
void display_idle(void);
void display_message(const char *line1, const char *line2, const char *line3);
void display_set_progress(float frac);  /* 0.0–1.0 */

#endif /* DISPLAY_H */