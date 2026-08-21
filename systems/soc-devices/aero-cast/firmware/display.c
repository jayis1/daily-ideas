/* display.c — SSD1306 OLED driver (128x64, I2C)
 *
 * Minimal frame-buffer based renderer for the Aero Cast.
 * Shows wind data, gust tracking, turbulence stats, and calibration.
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "display.h"
#include "sdkconfig.h"

#define OLED_WIDTH  128
#define OLED_HEIGHT 64
#define OLED_PAGES  8

static uint8_t fb[OLED_WIDTH * OLED_PAGES];  /* 1 KB frame buffer */

static void i2c_write_cmd(uint8_t cmd)
{
    uint8_t buf[2] = { 0x00, cmd };
    i2c_write_blocking(i2c0, SSD1306_I2C_ADDR, buf, 2, false);
}

static void i2c_write_data(uint8_t *data, size_t len)
{
    uint8_t buf[2];
    for (size_t i = 0; i < len; i++) {
        buf[0] = 0x40;
        buf[1] = data[i];
        i2c_write_blocking(i2c0, SSD1306_I2C_ADDR, buf, 2, false);
    }
}

/* Simple 5x7 font for digits and basic characters */
/* (Using a minimal subset — in production, use a proper font table) */

static void fb_clear(void)
{
    memset(fb, 0, sizeof(fb));
}

static void fb_set_pixel(int x, int y, bool on)
{
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;
    int page = y / 8;
    int bit = y % 8;
    if (on)
        fb[page * OLED_WIDTH + x] |= (1 << bit);
    else
        fb[page * OLED_WIDTH + x] &= ~(1 << bit);
}

/* Draw a horizontal line */
static void fb_hline(int x0, int x1, int y)
{
    if (x0 > x1) { int t = x0; x0 = x1; x1 = t; }
    for (int x = x0; x <= x1; x++)
        fb_set_pixel(x, y, true);
}

/* Draw a vertical line */
static void fb_vline(int x, int y0, int y1)
{
    if (y0 > y1) { int t = y0; y0 = y1; y1 = t; }
    for (int y = y0; y <= y1; y++)
        fb_set_pixel(x, y, true);
}

/* Minimal text rendering using a small 5x7 bitmap font */
/* Font table for digits 0-9, letters A-Z (upper), and some symbols */
static const uint8_t font5x7[][5] = {
    /* space */ {0x00,0x00,0x00,0x00,0x00},
    /* ! */     {0x00,0x00,0x5F,0x00,0x00},
    /* " */     {0x00,0x07,0x00,0x07,0x00},
    /* # */     {0x14,0x7F,0x14,0x7F,0x14},
    /* 0 */     {0x3E,0x51,0x49,0x45,0x3E},
    /* 1 */     {0x00,0x42,0x7F,0x40,0x00},
    /* 2 */     {0x42,0x61,0x51,0x49,0x46},
    /* 3 */     {0x21,0x41,0x45,0x4B,0x31},
    /* 4 */     {0x18,0x14,0x12,0x7F,0x10},
    /* 5 */     {0x27,0x45,0x45,0x45,0x39},
    /* 6 */     {0x3C,0x4A,0x49,0x49,0x30},
    /* 7 */     {0x01,0x71,0x09,0x05,0x03},
    /* 8 */     {0x36,0x49,0x49,0x49,0x36},
    /* 9 */     {0x06,0x49,0x49,0x29,0x1E},
    /* : */     {0x00,0x36,0x36,0x00,0x00},
    /* . */     {0x00,0x60,0x60,0x00,0x00},
    /* - */     {0x08,0x08,0x08,0x08,0x00},
    /* + */     {0x08,0x08,0x3E,0x08,0x08},
    /* A */     {0x7E,0x11,0x11,0x11,0x7E},
    /* B */     {0x7F,0x49,0x49,0x49,0x36},
    /* C */     {0x3E,0x41,0x41,0x41,0x22},
    /* D */     {0x7F,0x41,0x41,0x22,0x1C},
    /* E */     {0x7F,0x49,0x49,0x49,0x41},
    /* F */     {0x7F,0x09,0x09,0x09,0x01},
    /* G */     {0x3E,0x41,0x49,0x49,0x7A},
    /* H */     {0x7F,0x08,0x08,0x08,0x7F},
    /* I */     {0x00,0x41,0x7F,0x41,0x00},
    /* J */     {0x20,0x40,0x41,0x3F,0x01},
    /* K */     {0x7F,0x08,0x14,0x22,0x41},
    /* L */     {0x7F,0x40,0x40,0x40,0x40},
    /* M */     {0x7F,0x02,0x0C,0x02,0x7F},
    /* N */     {0x7F,0x04,0x08,0x10,0x7F},
    /* O */     {0x3E,0x41,0x41,0x41,0x3E},
    /* P */     {0x7F,0x09,0x09,0x09,0x06},
    /* Q */     {0x3E,0x41,0x51,0x21,0x5E},
    /* R */     {0x7F,0x09,0x19,0x29,0x46},
    /* S */     {0x46,0x49,0x49,0x49,0x31},
    /* T */     {0x01,0x01,0x7F,0x01,0x01},
    /* U */     {0x3F,0x40,0x40,0x40,0x3F},
    /* V */     {0x1F,0x20,0x40,0x20,0x1F},
    /* W */     {0x3F,0x40,0x38,0x40,0x3F},
    /* X */     {0x63,0x14,0x08,0x14,0x63},
    /* Y */     {0x07,0x08,0x70,0x08,0x07},
    /* Z */     {0x61,0x51,0x49,0x45,0x43},
    /* ° */     {0x0E,0x11,0x0E,0x00,0x00},
    /* m */     {0x7F,0x02,0x04,0x02,0x7F},
    /* s */     {0x46,0x49,0x49,0x49,0x31},
};

/* Map character to font index */
static int char_to_font(char c)
{
    if (c == ' ') return 0;
    if (c == '!') return 1;
    if (c == '"') return 2;
    if (c == '#') return 3;
    if (c >= '0' && c <= '9') return 4 + (c - '0');
    if (c == ':') return 14;
    if (c == '.') return 15;
    if (c == '-') return 16;
    if (c == '+') return 17;
    if (c >= 'A' && c <= 'Z') return 18 + (c - 'A');
    if (c == 0xB0) return 44;  /* ° */
    if (c >= 'a' && c <= 'z') {
        if (c == 'm') return 45;
        if (c == 's') return 46;
        return 0;  /* unsupported lowercase → space */
    }
    return 0;
}

static void fb_draw_char(int x, int y, char c)
{
    int idx = char_to_font(c);
    for (int col = 0; col < 5; col++) {
        uint8_t col_data = font5x7[idx][col];
        for (int row = 0; row < 7; row++) {
            if (col_data & (1 << row))
                fb_set_pixel(x + col, y + row, true);
        }
    }
}

static void fb_draw_string(int x, int y, const char *str)
{
    int cx = x;
    while (*str) {
        fb_draw_char(cx, y, *str);
        cx += 6;  /* 5 px font + 1 px spacing */
        str++;
    }
}

/* Draw a simple wind direction arrow */
static void fb_draw_arrow(int cx, int cy, int len, float angle_deg)
{
    float rad = angle_deg * M_PI / 180.0f;
    int dx = (int)(sin(rad) * len);
    int dy = -(int)(cos(rad) * len);
    int ex = cx + dx;
    int ey = cy + dy;

    /* Simple line approximation using Bresenham */
    int x0 = cx, y0 = cy, x1 = ex, y1 = ey;
    int dx_abs = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy_abs = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx_abs + dy_abs;
    while (1) {
        fb_set_pixel(x0, y0, true);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy_abs) { err += dy_abs; x0 += sx; }
        if (e2 <= dx_abs) { err += dx_abs; y0 += sy; }
    }
}

static void fb_flush(void)
{
    /* Set column and page address ranges, then write data */
    i2c_write_cmd(0x21);  /* set column address */
    i2c_write_cmd(0x00);
    i2c_write_cmd(0x7F);
    i2c_write_cmd(0x22);  /* set page address */
    i2c_write_cmd(0x00);
    i2c_write_cmd(0x07);

    /* Write framebuffer data */
    uint8_t buf[17];
    for (int i = 0; i < sizeof(fb); i += 16) {
        buf[0] = 0x40;
        memcpy(&buf[1], &fb[i], 16);
        i2c_write_blocking(i2c0, SSD1306_I2C_ADDR, buf, 17, false);
    }
}

void display_init(void)
{
    /* SSD1306 initialization sequence */
    i2c_write_cmd(0xAE);  /* display off */
    i2c_write_cmd(0xD5); i2c_write_cmd(0x80);  /* clock divide */
    i2c_write_cmd(0xA8); i2c_write_cmd(0x3F);  /* multiplex 1/64 */
    i2c_write_cmd(0xD3); i2c_write_cmd(0x00);  /* display offset */
    i2c_write_cmd(0x40);  /* start line 0 */
    i2c_write_cmd(0x8D); i2c_write_cmd(0x14);  /* charge pump on */
    i2c_write_cmd(0x20); i2c_write_cmd(0x00);  /* horizontal addressing */
    i2c_write_cmd(0xA1);  /* segment remap */
    i2c_write_cmd(0xC8);  /* COM scan direction */
    i2c_write_cmd(0xDA); i2c_write_cmd(0x12);  /* COM pins config */
    i2c_write_cmd(0x81); i2c_write_cmd(0xCF);  /* contrast */
    i2c_write_cmd(0xD9); i2c_write_cmd(0xF1);  /* pre-charge period */
    i2c_write_cmd(0xDB); i2c_write_cmd(0x40);  /* VCOMH deselect */
    i2c_write_cmd(0xA4);  /* display follows RAM */
    i2c_write_cmd(0xA6);  /* normal (not inverted) */
    i2c_write_cmd(0xAF);  /* display ON */

    fb_clear();
    fb_flush();
    printf("[display] SSD1306 initialized\n");
}

void display_clear(void)
{
    fb_clear();
    fb_flush();
}

void display_show_wind(const wind_vector_t *wind, const bme280_data_t *atm, float max_gust)
{
    char line[24];
    fb_clear();

    /* Top: wind speed and direction */
    snprintf(line, sizeof(line), "SPD %4.1f M/S", wind->speed);
    fb_draw_string(0, 0, line);

    snprintf(line, sizeof(line), "DIR %3.0f", wind->direction);
    fb_draw_string(0, 9, line);

    /* Wind direction arrow (center-right area) */
    fb_draw_arrow(96, 12, 12, wind->direction);

    /* Middle: gust */
    snprintf(line, sizeof(line), "GST %4.1f", max_gust);
    fb_draw_string(0, 18, line);

    /* W component (vertical) */
    snprintf(line, sizeof(line), "W %+4.2f", wind->w);
    fb_draw_string(0, 27, line);

    /* Bottom: sonic temp and atmospheric */
    snprintf(line, sizeof(line), "TS %4.1fC", wind->t_sonic - 273.15f);
    fb_draw_string(0, 36, line);

    if (atm) {
        snprintf(line, sizeof(line), "P %4.0fHPA", atm->pressure / 100.0f);
        fb_draw_string(0, 45, line);
        snprintf(line, sizeof(line), "RH %2.0f%% T %4.1f", atm->humidity, atm->temperature);
        fb_draw_string(0, 54, line);
    }

    fb_flush();
}

void display_show_gust(float max_gust, float max_dir, const wind_vector_t *current)
{
    char line[24];
    fb_clear();
    fb_draw_string(0, 0, "GUST MODE");
    snprintf(line, sizeof(line), "MAX %4.1f M/S", max_gust);
    fb_draw_string(0, 12, line);
    snprintf(line, sizeof(line), "DIR %3.0f", max_dir);
    fb_draw_string(0, 24, line);
    snprintf(line, sizeof(line), "NOW %4.1f", current->speed);
    fb_draw_string(0, 40, line);
    fb_flush();
}

void display_show_flux(const turbulence_stats_t *stats, uint32_t elapsed_s)
{
    char line[24];
    fb_clear();
    fb_draw_string(0, 0, "FLUX MODE");
    snprintf(line, sizeof(line), "TKE %4.2f", stats->tke);
    fb_draw_string(0, 10, line);
    snprintf(line, sizeof(line), "U* %4.2f", stats->u_star);
    fb_draw_string(0, 20, line);
    snprintf(line, sizeof(line), "SU %4.2f", stats->sigma_u);
    fb_draw_string(0, 30, line);
    snprintf(line, sizeof(line), "SW %4.2f", stats->sigma_w);
    fb_draw_string(0, 40, line);
    snprintf(line, sizeof(line), "N %4lus", elapsed_s);
    fb_draw_string(0, 54, line);
    fb_flush();
}

void display_show_profile(float avg_speed, float avg_dir, uint32_t samples)
{
    char line[24];
    fb_clear();
    fb_draw_string(0, 0, "PROFILE");
    snprintf(line, sizeof(line), "AVG %4.1f M/S", avg_speed);
    fb_draw_string(0, 14, line);
    snprintf(line, sizeof(line), "DIR %3.0f", avg_dir);
    fb_draw_string(0, 26, line);
    snprintf(line, sizeof(line), "N %lu", samples);
    fb_draw_string(0, 42, line);
    fb_flush();
}

void display_show_calibrate(int path, const path_result_t *paths)
{
    char line[24];
    fb_clear();
    fb_draw_string(0, 0, "CALIBRATE");
    for (int i = 0; i < NUM_PATHS; i++) {
        snprintf(line, sizeof(line), "P%d %6.1fus", i, paths[i].t_forward_us);
        fb_draw_string(0, 12 + i * 12, line);
    }
    fb_flush();
}

void display_show_status(const char *msg)
{
    fb_clear();
    fb_draw_string(0, 28, msg);
    fb_flush();
}