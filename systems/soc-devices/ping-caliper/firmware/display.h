/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * display.h — SSD1306 OLED driver, A-scan renderer, menu system
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include "config.h"
#include "receiver.h"
#include "thickness.h"
#include "flaw.h"

typedef enum {
    UI_PAGE_ASCAN = 0,    /* live A-scan + thickness readout             */
    UI_PAGE_MENU,         /* settings menu                                */
    UI_PAGE_CALIBRATE,    /* calibration flow                             */
    UI_PAGE_LOG,          /* SD log browser                               */
    UI_PAGE_INFO,         /* about / version                              */
} ui_page_t;

void display_init(void);
void display_clear(void);
void display_flush(void);

/* Draw the main A-scan page. */
void display_draw_ascan(const ascan_t *scan,
                         const thickness_result_t *thk,
                         const flaw_result_t *flaw,
                         const char *material_name,
                         uint8_t battery_pct);

/* Menu API. */
void display_menu_set_root(void);
void display_menu_draw(void);
int8_t display_menu_select(void);     /* returns 1 if action taken */
void display_menu_up(void);
void display_menu_down(void);
void display_menu_back(void);

/* Generic text rendering. */
void display_text(uint8_t x, uint8_t y, const char *s);
void display_text_f(uint8_t x, uint8_t y, const char *fmt, ...);
void display_set_page(ui_page_t page);
ui_page_t display_get_page(void);

/* Set contrast (0..255). */
void display_set_contrast(uint8_t val);

#endif /* DISPLAY_H */