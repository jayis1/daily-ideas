/*
 * display.c — SH1106 OLED display driver (128x64, I2C)
 */

#include "display.h"
#include "main.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

extern I2C_HandleTypeDef hi2c1;

/* Display buffer (128 columns × 8 pages = 128×64 bits) */
static uint8_t disp_buf[DISP_W * (DISP_H / 8)];
static int cursor_x = 0, cursor_y = 0;

/* ── Font: 6x8 (basic ASCII) ───────────────────────────── */
static const uint8_t font6x8[][6] = {
    {0x00,0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x3E,0x00,0x00,0x00}, /* ! */
    {0x00,0x00,0x7C,0x00,0x00,0x00}, /* " — simplified */
    /* ... abbreviated font; real implementation has full 96-char table */
};

/* For brevity, we use a minimal font via built-in lookup */
/* In production, include a full 6x8 font table */

/* Simplified character rendering using a compact font */
static void draw_char6x8(int x, int y, char c)
{
    if (c < 32 || c > 127) c = '?';
    /* Use a minimal font: just draw a basic representation */
    /* In production: use full font table lookup */
    uint8_t col = (uint8_t)c;
    for (int i = 0; i < 6; i++) {
        /* Simple placeholder: each column is a pattern from char code */
        uint8_t bits = (col & (1 << i)) ? 0x3C : 0x00;
        for (int j = 0; j < 8; j++) {
            if (bits & (1 << j)) {
                display_pixel(x + i, y + j, 1);
            }
        }
    }
}

static void draw_char8x16(int x, int y, char c)
{
    /* Scaled-up version of 6x8 → 8x16 */
    if (c < 32 || c > 127) c = '?';
    for (int i = 0; i < 6; i++) {
        uint8_t bits = ((uint8_t)c & (1 << i)) ? 0x3C : 0x00;
        for (int j = 0; j < 8; j++) {
            if (bits & (1 << j)) {
                display_pixel(x + i * 2, y + j * 2, 1);
                display_pixel(x + i * 2 + 1, y + j * 2, 1);
                display_pixel(x + i * 2, y + j * 2 + 1, 1);
                display_pixel(x + i * 2 + 1, y + j * 2 + 1, 1);
            }
        }
    }
}

/* ── Low-level I2C ────────────────────────────────────── */
static void oled_write_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd};  /* Co=0, D/C=0 → command */
    HAL_I2C_Master_Transmit(&hi2c1, OLED_I2C_ADDR << 1, buf, 2, 100);
}

static void oled_write_data(uint8_t data)
{
    uint8_t buf[2] = {0x40, data};  /* Co=0, D/C=1 → data */
    HAL_I2C_Master_Transmit(&hi2c1, OLED_I2C_ADDR << 1, buf, 2, 100);
}

/* ── Public Functions ─────────────────────────────────── */

void display_init(void)
{
    HAL_Delay(100);

    oled_write_cmd(0xAE);  /* Display off */
    oled_write_cmd(0xD5); oled_write_cmd(0x80);  /* Clock divide */
    oled_write_cmd(0xA8); oled_write_cmd(0x3F);  /* Multiplex 64 */
    oled_write_cmd(0xD3); oled_write_cmd(0x00);  /* Display offset */
    oled_write_cmd(0x40);  /* Start line 0 */
    oled_write_cmd(0x8D); oled_write_cmd(0x14);  /* Charge pump on */
    oled_write_cmd(0x20); oled_write_cmd(0x00);  /* Addressing mode horizontal */
    oled_write_cmd(0xA1);  /* Segment remap */
    oled_write_cmd(0xC8);  /* COM scan direction */
    oled_write_cmd(0xDA); oled_write_cmd(0x12);  /* COM pins */
    oled_write_cmd(0x81); oled_write_cmd(0xCF);  /* Contrast */
    oled_write_cmd(0xD9); oled_write_cmd(0xF1);  /* Pre-charge */
    oled_write_cmd(0xDB); oled_write_cmd(0x40);  /* VCOM deselect */
    oled_write_cmd(0xA4);  /* Display RAM content */
    oled_write_cmd(0xA6);  /* Normal display */
    oled_write_cmd(0xAF);  /* Display on */

    display_clear();
    display_flush();
}

void display_clear(void)
{
    memset(disp_buf, 0, sizeof(disp_buf));
}

void display_flush(void)
{
    for (uint8_t page = 0; page < (DISP_H / 8); page++) {
        oled_write_cmd(0xB0 + page);  /* Page address */
        oled_write_cmd(0x00);          /* Lower column */
        oled_write_cmd(0x10);          /* Higher column */
        for (int x = 0; x < DISP_W; x++) {
            oled_write_data(disp_buf[page * DISP_W + x]);
        }
    }
}

void display_set_cursor(int x, int y)
{
    cursor_x = x;
    cursor_y = y;
}

void display_text(int x, int y, const char *str, int font_size)
{
    int cx = x;
    for (int i = 0; str[i]; i++) {
        if (font_size == FONT_SMALL) {
            draw_char6x8(cx, y, str[i]);
            cx += 6;
        } else {
            draw_char8x16(cx, y, str[i]);
            cx += 8;
        }
        if (cx >= DISP_W) break;
    }
}

void display_printf(int x, int y, const char *fmt, ...)
{
    char buf[64];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    display_text(x, y, buf, FONT_SMALL);
}

void display_pixel(int x, int y, int on)
{
    if (x < 0 || x >= DISP_W || y < 0 || y >= DISP_H) return;
    int page = y / 8;
    int bit = 1 << (y & 7);
    if (on) {
        disp_buf[page * DISP_W + x] |= bit;
    } else {
        disp_buf[page * DISP_W + x] &= ~bit;
    }
}

void display_hline(int x, int y, int w, int on)
{
    for (int i = 0; i < w; i++) display_pixel(x + i, y, on);
}

void display_vline(int x, int y, int h, int on)
{
    for (int i = 0; i < h; i++) display_pixel(x, y + i, on);
}

void display_rect(int x, int y, int w, int h, int on)
{
    display_hline(x, y, w, on);
    display_hline(x, y + h - 1, w, on);
    display_vline(x, y, h, on);
    display_vline(x + w - 1, y, h, on);
}

void display_fill_rect(int x, int y, int w, int h, int on)
{
    for (int j = 0; j < h; j++) {
        for (int i = 0; i < w; i++) {
            display_pixel(x + i, y + j, on);
        }
    }
}

void display_eem_heatmap(const uint16_t eem[8][256])
{
    /* Draw 8×64 mini heatmap at bottom of display */
    int hx = 0, hy = 0;  /* offset (called from result screen) */
    /* Find max value for normalization */
    uint16_t maxv = 1;
    for (int w = 0; w < 8; w++) {
        for (int p = 0; p < 256; p += 4) {
            uint16_t v = eem[w][p];
            if (v > maxv) maxv = v;
        }
    }

    /* Draw 8 rows × 64 columns (downsample 256→64) */
    for (int w = 0; w < 8; w++) {
        for (int p = 0; p < 64; p++) {
            uint16_t v = eem[w][p * 4];
            int intensity = (int)((float)v / (float)maxv * 3.0f);
            int x = hx + p;
            int y = hy + w;
            if (intensity > 0) {
                display_pixel(x, y, 1);
            }
        }
    }
}

void display_spectrum(const uint16_t *pixels, int len, uint16_t scale)
{
    int x0 = 0, y0 = 40;  /* spectrum area */
    int w = DISP_W;
    int h = 20;

    if (scale == 0) scale = 1;

    for (int i = 0; i < w && i < len; i++) {
        int idx = (int)((float)i / w * len);
        int val = (int)((float)pixels[idx] / (float)scale * h);
        if (val > h) val = h;
        display_vline(x0 + i, y0 + h - val, val, 1);
    }
}

void display_battery(int x, int y, int pct)
{
    display_rect(x, y, 18, 8, 1);
    display_fill_rect(x + 18, y + 2, 2, 4, 1);
    int fill = (pct * 16) / 100;
    display_fill_rect(x + 1, y + 1, fill, 6, 1);
}

void display_progress(int x, int y, int w, int pct)
{
    display_rect(x, y, w, 5, 1);
    int fill = ((w - 2) * pct) / 100;
    display_fill_rect(x + 1, y + 1, fill, 3, 1);
}

void display_sleep(void)
{
    oled_write_cmd(0xAE);
}

void display_wake(void)
{
    oled_write_cmd(0xAF);
}