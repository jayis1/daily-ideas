/*
 * Flux Ring — oled_display.c
 * SSD1306 32x64 monochrome OLED display driver.
 *
 * Uses a small framebuffer (32*64/8 = 256 bytes) and
 * renders text + graphics for field data display.
 *
 * SPDX-License-Identifier: MIT
 */

#include "oled_display.h"
#include <zephyr/kernel.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/logging/log.h>
#include <stdio.h>
#include <string.h>

LOG_MODULE_DECLARE(oled_display, LOG_LEVEL_INF);

#define SSD1306_I2C_ADDR    0x3C
#define SSD1306_WIDTH       64
#define SSD1306_HEIGHT      32
#define SSD1306_PAGES       (SSD1306_HEIGHT / 8)  /* 4 pages */
#define FB_SIZE             (SSD1306_WIDTH * SSD1306_PAGES)

/* SSD1306 commands */
#define SSD1306_DISPLAY_OFF         0xAE
#define SSD1306_DISPLAY_ON          0xAF
#define SSD1306_SET_DISPLAY_OFFSET  0xD3
#define SSD1306_SET_MUX_RATIO       0xA8
#define SSD1306_SET_START_LINE      0x40
#define SSD1306_SET_SEGMENT_MAP     0xA1
#define SSD1306_SET_COM_SCAN_MODE   0xC8
#define SSD1306_SET_COM_PIN_CFG     0xDA
#define SSD1306_SET_CONTRAST        0x81
#define SSD1306_SET_PRECHARGE       0xD9
#define SSD1306_SET_VCOM_DETECT     0xDB
#define SSD1306_SET_OSC_FREQ        0xD5
#define SSD1306_SET_CHARGE_PUMP     0x8D
#define SSD1306_SET_MEMORY_MODE     0x20
#define SSD1306_SET_COL_ADDR        0x21
#define SSD1306_SET_PAGE_ADDR       0x22

static const struct device *i2c_dev;
static uint8_t framebuffer[FB_SIZE];
static bool display_on = false;

/* Mini 5x7 font (printable ASCII 32-127) */
#include "font_5x7.h"

static int send_cmd(uint8_t cmd)
{
    uint8_t buf[2] = { 0x00, cmd };  /* Control byte 0x00 = command */
    return i2c_write(i2c_dev, buf, 2, SSD1306_I2C_ADDR);
}

static int send_data(const uint8_t *data, uint16_t len)
{
    /* First byte is 0x40 = data stream */
    uint8_t buf[FB_SIZE + 1];
    buf[0] = 0x40;
    memcpy(&buf[1], data, len);
    return i2c_write(i2c_dev, buf, len + 1, SSD1306_I2C_ADDR);
}

static void fb_clear(void)
{
    memset(framebuffer, 0, FB_SIZE);
}

static void fb_set_pixel(uint8_t x, uint8_t y, bool on)
{
    if (x >= SSD1306_WIDTH || y >= SSD1306_HEIGHT) return;
    uint16_t idx = x + (y / 8) * SSD1306_WIDTH;
    uint8_t bit = 1 << (y % 8);
    if (on) framebuffer[idx] |= bit;
    else    framebuffer[idx] &= ~bit;
}

static void fb_draw_char(uint8_t x, uint8_t y, char c)
{
    if (c < 32 || c > 127) c = '?';
    const uint8_t *glyph = &font_5x7[(c - 32) * 5];
    for (int col = 0; col < 5; col++) {
        uint8_t line = glyph[col];
        for (int row = 0; row < 7; row++) {
            if (line & (1 << row)) {
                fb_set_pixel(x + col, y + row, true);
            }
        }
    }
}

static void fb_draw_string(uint8_t x, uint8_t y, const char *str)
{
    while (*str && x < SSD1306_WIDTH - 5) {
        fb_draw_char(x, y, *str);
        x += 6;
        str++;
    }
}

static void fb_draw_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h,
                        float fraction)
{
    if (fraction < 0) fraction = 0;
    if (fraction > 1) fraction = 1;
    uint8_t filled = (uint8_t)(w * fraction);
    for (int i = 0; i < w; i++) {
        for (int j = 0; j < h; j++) {
            fb_set_pixel(x + i, y + j, i < filled);
        }
    }
}

static void fb_flush(void)
{
    /* Set column and page address range */
    send_cmd(SSD1306_SET_COL_ADDR);
    send_cmd(32);   /* Column offset for 64-wide display */
    send_cmd(95);
    send_cmd(SSD1306_SET_PAGE_ADDR);
    send_cmd(0);
    send_cmd(SSD1306_PAGES - 1);

    send_data(framebuffer, FB_SIZE);
}

int oled_display_init(void)
{
    i2c_dev = DEVICE_DT_GET(DT_NODELABEL(i2c0));
    if (!device_is_ready(i2c_dev)) {
        LOG_ERR("I2C not ready for SSD1306");
        return -1;
    }

    /* Initialization sequence */
    send_cmd(SSD1306_DISPLAY_OFF);
    send_cmd(SSD1306_SET_MUX_RATIO);    send_cmd(31);   /* Mux ratio 32 */
    send_cmd(SSD1306_SET_DISPLAY_OFFSET); send_cmd(0);
    send_cmd(SSD1306_SET_START_LINE | 0);
    send_cmd(SSD1306_SET_SEGMENT_MAP);     /* Column addr 0->63 */
    send_cmd(SSD1306_SET_COM_SCAN_MODE);   /* COM scan normal */
    send_cmd(SSD1306_SET_COM_PIN_CFG);   send_cmd(0x02);
    send_cmd(SSD1306_SET_CONTRAST);      send_cmd(0x8F);
    send_cmd(SSD1306_SET_PRECHARGE);     send_cmd(0xF1);
    send_cmd(SSD1306_SET_VCOM_DETECT);  send_cmd(0x40);
    send_cmd(SSD1306_SET_MEMORY_MODE);  send_cmd(0x00); /* Horizontal */
    send_cmd(SSD1306_SET_OSC_FREQ);      send_cmd(0x80);
    send_cmd(SSD1306_SET_CHARGE_PUMP);   send_cmd(0x14); /* Enable */
    send_cmd(SSD1306_DISPLAY_ON);

    display_on = true;
    fb_clear();
    fb_draw_string(4, 0, "FLUX RING");
    fb_draw_string(4, 12, "v1.0");
    fb_flush();

    LOG_INF("SSD1306 OLED initialized (64x32)");
    return 0;
}

void oled_display_update(const field_vector_t *field, float magnitude,
                         compass_heading_t heading, pole_t pole,
                         disp_mode_t mode, uint8_t battery_pct)
{
    char buf[16];

    fb_clear();

    switch (mode) {
    case DISP_MODE_MONITOR:
        /* Minimal display: magnitude only */
        snprintf(buf, sizeof(buf), "%.1fG", magnitude);
        fb_draw_string(2, 0, buf);
        snprintf(buf, sizeof(buf), "MON %d%%", battery_pct);
        fb_draw_string(2, 10, buf);
        break;

    case DISP_MODE_EXPLORE:
        /* Full field display */
        snprintf(buf, sizeof(buf), "%.2fG", magnitude);
        fb_draw_string(2, 0, buf);

        /* Compass heading */
        snprintf(buf, sizeof(buf), "%d%c %s", heading, 0xF8,
                 compass_cardinal(heading));
        fb_draw_string(2, 10, buf);

        /* Magnitude bar */
        float bar_frac = magnitude / 50.0f;
        if (bar_frac > 1.0f) bar_frac = 1.0f;
        fb_draw_bar(2, 22, 60, 4, bar_frac);

        /* Pole indicator */
        if (pole == POLE_N) fb_draw_string(52, 0, "N");
        else if (pole == POLE_S) fb_draw_string(52, 0, "S");
        break;

    case DISP_MODE_MAPPING:
        /* Mapping mode indicator */
        fb_draw_string(2, 0, "MAP");
        snprintf(buf, sizeof(buf), "%.1fG", magnitude);
        fb_draw_string(30, 0, buf);
        snprintf(buf, sizeof(buf), "%d%%", battery_pct);
        fb_draw_string(46, 10, buf);

        /* Blinking recording dot (alternates) */
        static int dot_toggle = 0;
        if (++dot_toggle % 2) {
            fb_set_pixel(60, 2, true);
            fb_set_pixel(61, 2, true);
            fb_set_pixel(60, 3, true);
            fb_set_pixel(61, 3, true);
        }
        break;

    case DISP_MODE_COMPASS:
        /* Large compass heading */
        snprintf(buf, sizeof(buf), "%03d", heading);
        /* Draw large digits would need bigger font — using small for now */
        fb_draw_string(10, 0, buf);
        fb_draw_string(10, 12, compass_cardinal(heading));

        /* Simple compass rose indicator (8 pixels around center) */
        int cx = 56, cy = 16;
        /* N */
        fb_set_pixel(cx, cy - 4, true);
        /* NE */
        fb_set_pixel(cx + 3, cy - 3, true);
        /* E */
        fb_set_pixel(cx + 4, cy, true);
        /* SE */
        fb_set_pixel(cx + 3, cy + 3, true);
        /* S */
        fb_set_pixel(cx, cy + 4, true);
        /* SW */
        fb_set_pixel(cx - 3, cy + 3, true);
        /* W */
        fb_set_pixel(cx - 4, cy, true);
        /* NW */
        fb_set_pixel(cx - 3, cy - 3, true);

        /* Direction dot */
        float rad = heading * 3.14159265f / 180.0f;
        int dx = (int)(3.5f * sinf(rad));
        int dy = -(int)(3.5f * cosf(rad));
        fb_set_pixel(cx + dx, cy + dy, true);
        break;
    }

    fb_flush();
}

void oled_display_calibrating(void)
{
    fb_clear();
    fb_draw_string(2, 0, "CALIBRATE");
    fb_draw_string(2, 12, "rotate...");

    /* Animated dots */
    static int dot_count = 0;
    for (int i = 0; i < (dot_count % 4); i++) {
        fb_set_pixel(2 + i * 8, 24, true);
    }
    dot_count++;
    fb_flush();
}

void oled_display_cal_ok(void)
{
    fb_clear();
    fb_draw_string(8, 0, "CAL OK!");
    fb_flush();
    k_msleep(1500);
}

void oled_display_off(void)
{
    if (display_on) {
        send_cmd(SSD1306_DISPLAY_OFF);
        display_on = false;
    }
}

void oled_display_on(void)
{
    if (!display_on) {
        send_cmd(SSD1306_DISPLAY_ON);
        display_on = true;
    }
}