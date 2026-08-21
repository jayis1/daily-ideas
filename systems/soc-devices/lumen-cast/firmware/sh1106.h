/**
 * lumen_cast/firmware/sh1106.h — OLED display driver
 */
#ifndef LUMEN_CAST_SH1106_H
#define LUMEN_CAST_SH1106_H

int sh1106_init(void);
void sh1106_draw_idle(void);
void sh1106_draw_scanning(const scan_buffer_t *s, float az, float el, uint8_t batt);
void sh1106_draw_results(const photo_result_t *r, uint8_t batt);
void sh1106_draw_polar(const scan_buffer_t *s);
void sh1106_draw_settings(const scan_config_t *c, int field);

#endif