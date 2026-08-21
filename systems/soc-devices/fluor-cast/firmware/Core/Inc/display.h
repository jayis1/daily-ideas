/*
 * display.h — SH1106 OLED display driver (128x64, I2C)
 */

#ifndef DISPLAY_H
#define DISPLAY_H

#include <stdint.h>

/* Display dimensions */
#define DISP_W 128
#define DISP_H 64

/* Font sizes */
#define FONT_SMALL  1   /* 6x8 */
#define FONT_MED    2   /* 8x16 */
#define FONT_LARGE  3   /* 16x16 */

/**
 * Initialize OLED display.
 */
void display_init(void);

/**
 * Clear display buffer.
 */
void display_clear(void);

/**
 * Push display buffer to OLED.
 */
void display_flush(void);

/**
 * Set cursor position.
 */
void display_set_cursor(int x, int y);

/**
 * Draw text at cursor position.
 */
void display_text(int x, int y, const char *str, int font_size);

/**
 * Draw text with printf formatting.
 */
void display_printf(int x, int y, const char *fmt, ...);

/**
 * Draw a single pixel.
 */
void display_pixel(int x, int y, int on);

/**
 * Draw horizontal line.
 */
void display_hline(int x, int y, int w, int on);

/**
 * Draw vertical line.
 */
void display_vline(int x, int y, int h, int on);

/**
 * Draw rectangle outline.
 */
void display_rect(int x, int y, int w, int h, int on);

/**
 * Draw filled rectangle.
 */
void display_fill_rect(int x, int y, int w, int h, int on);

/**
 * Draw a miniature EEM heatmap on the display.
 * 8 rows (excitation) × 64 cols (downsampled emission).
 */
void display_eem_heatmap(const uint16_t eem[8][256]);

/**
 * Draw a single emission spectrum curve.
 */
void display_spectrum(const uint16_t *pixels, int len, uint16_t scale);

/**
 * Draw battery icon with level.
 * @param pct  0–100
 */
void display_battery(int x, int y, int pct);

/**
 * Draw a simple progress bar.
 */
void display_progress(int x, int y, int w, int pct);

/**
 * Power off display (sleep mode).
 */
void display_sleep(void);

/**
 * Wake up display.
 */
void display_wake(void);

#endif /* DISPLAY_H */