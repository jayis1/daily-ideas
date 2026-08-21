/*
 * Pulse Hound — RF Signal Hunter
 * display.c — SSD1306 OLED driver, waterfall rendering, compass, digital readout
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "display.h"
#include "spectrum.h"
#include "classifier.h"
#include "config.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

/* ---- I2C HAL stubs ---- */
extern int  i2c_write(uint8_t addr, const uint8_t *data, uint8_t len);
extern int  i2c_write_reg(uint8_t addr, uint8_t reg, const uint8_t *data, uint8_t len);
extern void delay_ms(uint32_t ms);

/* ---- SSD1306 framebuffer (128×64 / 8 = 1024 bytes, 1 bit per pixel) ---- */
static uint8_t oled_fb[SSD1306_WIDTH * SSD1306_HEIGHT / 8];
static int display_initialized = 0;

/* ---- SSD1306 commands ---- */
enum {
    SSD1306_SET_CONTRAST       = 0x81,
    SSD1306_DISPLAY_ON         = 0xAF,
    SSD1306_DISPLAY_OFF        = 0xAE,
    SSD1306_NORMAL_DISPLAY     = 0xA4,
    SSD1306_INVERT_DISPLAY     = 0xA7,
    SSD1306_SET_MUX_RATIO      = 0xA8,
    SSD1306_SET_DISPLAY_OFFSET = 0xD3,
    SSD1306_SET_START_LINE     = 0x40,
    SSD1306_SET_SEGMENT_REMAP  = 0xA1,
    SSD1306_SET_COM_SCAN_DEC   = 0xC8,
    SSD1306_SET_COM_PINS       = 0xDA,
    SSD1306_SET_PRECHARGE      = 0xD9,
    SSD1306_SET_VCOM_DETECT    = 0xDB,
    SSD1306_SET_OSC_FREQ       = 0xD5,
    SSD1306_CHARGE_PUMP        = 0x8D,
};

static void ssd1306_command(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd}; /* control byte 0x00 = command */
    i2c_write(SSD1306_ADDR, buf, 2);
}

static void ssd1306_data(const uint8_t *data, int len)
{
    /* I2C: send control byte 0x40 (data) + data bytes */
    /* Split into chunks of 16 bytes (I2C buffer limit) */
    for (int i = 0; i < len; i += 16) {
        uint8_t buf[17];
        buf[0] = 0x40; /* data control byte */
        int chunk = len - i;
        if (chunk > 16) chunk = 16;
        memcpy(&buf[1], &data[i], chunk);
        i2c_write(SSD1306_ADDR, buf, chunk + 1);
    }
}

/* ---- Pixel operations ---- */
void display_set_pixel(int x, int y, int on)
{
    if (x < 0 || x >= SSD1306_WIDTH || y < 0 || y >= SSD1306_HEIGHT) return;
    int byte_idx = x + (y / 8) * SSD1306_WIDTH;
    if (on)
        oled_fb[byte_idx] |= (1 << (y & 7));
    else
        oled_fb[byte_idx] &= ~(1 << (y & 7));
}

void display_clear(void)
{
    memset(oled_fb, 0, sizeof(oled_fb));
}

/* ---- 5x7 font (compact subset for numbers + labels) ---- */
static const uint8_t font5x7[][5] = {
    /* 0-9 */
    {0x3E,0x51,0x49,0x45,0x3E}, {0x00,0x42,0x7F,0x40,0x00},
    {0x42,0x61,0x51,0x49,0x46}, {0x21,0x41,0x45,0x4B,0x31},
    {0x18,0x14,0x12,0x7F,0x10}, {0x27,0x45,0x45,0x45,0x39},
    {0x3C,0x4A,0x49,0x49,0x30}, {0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36}, {0x06,0x49,0x49,0x29,0x1E},
    /* A-Z (subset used in labels) */
    {0x7E,0x11,0x11,0x11,0x7E}, /* A at index 10 */
    {0x7F,0x49,0x49,0x49,0x36}, /* B */
    {0x3E,0x41,0x41,0x41,0x22}, /* C */
    {0x7F,0x41,0x41,0x22,0x1C}, /* D */
    {0x7F,0x49,0x49,0x49,0x41}, /* E */
    {0x7F,0x09,0x09,0x09,0x01}, /* F */
    {0x3E,0x41,0x49,0x49,0x7A}, /* G */
    {0x7F,0x08,0x08,0x08,0x7F}, /* H */
    {0x00,0x41,0x7F,0x41,0x00}, /* I */
    {0x20,0x40,0x41,0x3F,0x01}, /* J */
    {0x7F,0x08,0x14,0x22,0x41}, /* K */
    {0x7F,0x40,0x40,0x40,0x40}, /* L */
    {0x7F,0x02,0x0C,0x02,0x7F}, /* M */
    {0x7F,0x04,0x08,0x10,0x7F}, /* N */
    {0x3E,0x41,0x41,0x41,0x3E}, /* O */
    {0x7F,0x09,0x09,0x09,0x06}, /* P */
    {0x3E,0x41,0x51,0x21,0x5E}, /* Q */
    {0x7F,0x09,0x19,0x29,0x46}, /* R */
    {0x46,0x49,0x49,0x49,0x31}, /* S */
    {0x01,0x01,0x7F,0x01,0x01}, /* T */
    {0x3F,0x40,0x40,0x40,0x3F}, /* U */
    {0x1F,0x20,0x40,0x20,0x1F}, /* V */
    {0x3F,0x40,0x38,0x40,0x3F}, /* W */
    {0x63,0x14,0x08,0x14,0x63}, /* X */
    {0x07,0x08,0x70,0x08,0x07}, /* Y */
    {0x61,0x51,0x49,0x45,0x43}, /* Z */
};

static int char_to_font_idx(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'Z') return 10 + (c - 'A');
    return -1;
}

void display_draw_char(int x, int y, char c)
{
    int idx = char_to_font_idx(c);
    if (idx < 0) {
        /* Draw space / unknown as blank */
        for (int i = 0; i < 5; i++)
            for (int j = 0; j < 7; j++)
                display_set_pixel(x + i, y + j, 0);
        return;
    }
    for (int col = 0; col < 5; col++) {
        uint8_t bits = font5x7[idx][col];
        for (int row = 0; row < 7; row++) {
            display_set_pixel(x + col, y + row, (bits >> row) & 1);
        }
    }
}

void display_draw_text(int x, int y, const char *text)
{
    int x_pos = x;
    for (const char *p = text; *p; p++) {
        if (*p == ' ') {
            x_pos += 5; /* space width */
            continue;
        }
        display_draw_char(x_pos, y, *p >= 'a' && *p <= 'z' ? *p - 32 : *p);
        x_pos += 6; /* 5 px + 1 px spacing */
    }
}

void display_draw_text_p(int x, int y, const char *text)
{
    display_draw_text(x, y, text);
}

/* ---- Waterfall rendering ---- */
static void render_waterfall_row(int display_row, int y_offset)
{
    uint8_t row_data[WATERFALL_COLS];
    spectrum_get_row(display_row, row_data);

    /* Map 96 waterfall columns to the left 96 display columns */
    for (int x = 0; x < WATERFALL_COLS; x++) {
        /* Convert 8-bit intensity to dithered 1-bit pattern */
        uint8_t intensity = row_data[x];
        /* Simple threshold dithering: intensity > 128 → on */
        int on = (intensity > 128);
        /* Add Bayer dithering for smoother gradients */
        int bayer = ((x & 1) + (y_offset & 1)) ? 1 : 0;
        int threshold = 128 + (bayer ? 16 : -16);
        on = (intensity > threshold) ? 1 : 0;
        display_set_pixel(x, y_offset, on);
    }
}

/* ---- Compass arrow ---- */
static void draw_compass_arrow(int cx, int cy, int radius, float bearing_deg)
{
    /* Simple arrow: line from center to edge at bearing angle */
    float rad = bearing_deg * 3.14159265f / 180.0f;
    /* Adjust: 0° = up, 90° = right (compass convention) */
    float dx = sinf(rad) * radius;
    float dy = -cosf(rad) * radius;

    /* Draw line via Bresenham */
    int x0 = cx, y0 = cy;
    int x1 = cx + (int)dx, y1 = cy + (int)dy;
    int dx_abs = abs(x1 - x0), dy_abs = abs(y1 - y0);
    int sx = (x0 < x1) ? 1 : -1;
    int sy = (y0 < y1) ? 1 : -1;
    int err = dx_abs - dy_abs;

    while (1) {
        display_set_pixel(x0, y0, 1);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 > -dy_abs) { err -= dy_abs; x0 += sx; }
        if (e2 <  dx_abs) { err += dx_abs; y0 += sy; }
    }

    /* Arrowhead: two short lines at the tip */
    float head_rad = rad + 2.7f; /* ~155° back */
    int hx = x1 + (int)(sinf(head_rad) * 3);
    int hy = y1 + (int)(-cosf(head_rad) * 3);
    /* Draw head line 1 */
    int tx = x1, ty = y1;
    int hdx = abs(hx - tx), hdy = abs(hy - ty);
    int hsx = (tx < hx) ? 1 : -1, hsy = (ty < hy) ? 1 : -1;
    int herr = hdx - hdy;
    for (int i = 0; i < 4 && !(tx == hx && ty == hy); i++) {
        display_set_pixel(tx, ty, 1);
        int he2 = 2 * herr;
        if (he2 > -hdy) { herr -= hdy; tx += hsx; }
        if (he2 < hdx) { herr += hdx; ty += hsy; }
    }
}

/* ---- Full frame render ---- */
void display_render(float rssi_dbm, float peak_rssi, signal_class_t cls,
                    float bearing_deg, int battery_pct,
                    pulse_hound_mode_t mode, int audio_on)
{
    display_clear();

    /* --- Left: waterfall (96 columns × 64 rows) --- */
    for (int row = 0; row < SSD1306_HEIGHT; row++) {
        int wf_row = row; /* 1:1 mapping (newest at top) */
        render_waterfall_row(wf_row, row);
    }

    /* --- Right: info panel (columns 96–127, 32 px wide) --- */
    int info_x = DISPLAY_WATERFALL_WIDTH; /* 96 */

    /* RSSI value (top) */
    char buf[8];
    int rssi_int = (int)(rssi_dbm * 10.0f);
    snprintf(buf, sizeof(buf), "%4d", rssi_int);
    display_draw_text(info_x, 0, buf);
    display_draw_text(info_x + 24, 0, "dB");

    /* Peak hold */
    int peak_int = (int)(peak_rssi * 10.0f);
    snprintf(buf, sizeof(buf), "PK%3d", peak_int);
    display_draw_text(info_x, 10, buf);

    /* Classification label (abbreviated) */
    const char *label;
    switch (cls) {
        case CLASS_CW:       label = "CW"; break;
        case CLASS_WIFI_BLE:  label = "WFL"; break;
        case CLASS_CELLULAR:  label = "CEL"; break;
        case CLASS_RADAR:     label = "RAD"; break;
        case CLASS_THERMAL:   label = "THM"; break;
        default:              label = "???"; break;
    }
    display_draw_text(info_x, 22, label);

    /* Compass + bearing (middle area) */
    int compass_cx = info_x + 16;
    int compass_cy = 40;
    draw_compass_arrow(compass_cx, compass_cy, 8, bearing_deg);
    /* Circle outline (approximate) */
    for (int a = 0; a < 360; a += 15) {
        float rad = a * 3.14159265f / 180.0f;
        display_set_pixel(compass_cx + (int)(sinf(rad) * 8),
                          compass_cy + (int)(-cosf(rad) * 8), 1);
    }

    /* Bearing text */
    int brg_int = (int)bearing_deg;
    snprintf(buf, sizeof(buf), "%3d", brg_int);
    display_draw_text(info_x, 52, buf);

    /* Battery % (bottom right corner) */
    snprintf(buf, sizeof(buf), "%2d%%", battery_pct);
    display_draw_text(info_x, 58, buf);

    /* Mode indicator (top-right corner, tiny) */
    const char *mode_letter;
    switch (mode) {
        case MODE_SWEEP:    mode_letter = "S"; break;
        case MODE_DF:       mode_letter = "D"; break;
        case MODE_MONITOR:  mode_letter = "M"; break;
        case MODE_POWER_SAVE: mode_letter = "P"; break;
        default:            mode_letter = "?"; break;
    }
    display_draw_char(info_x + 24, 58, mode_letter[0]);

    /* Audio indicator */
    if (audio_on) display_draw_char(info_x + 30, 58, 'A');
}

/* ---- Flush framebuffer to OLED ---- */
void display_flush(void)
{
    /* Set column address range 0–127, page address range 0–7 */
    ssd1306_command(0x21); /* set column address */
    ssd1306_command(0x00);
    ssd1306_command(SSD1306_WIDTH - 1);
    ssd1306_command(0x22); /* set page address */
    ssd1306_command(0x00);
    ssd1306_command((SSD1306_HEIGHT / 8) - 1);

    /* Send framebuffer data */
    ssd1306_data(oled_fb, sizeof(oled_fb));
}

/* ---- Init ---- */
void display_init(void)
{
    if (display_initialized) return;

    /* SSD1306 initialization sequence */
    ssd1306_command(SSD1306_DISPLAY_OFF);
    ssd1306_command(SSD1306_SET_MUX_RATIO);    ssd1306_command(0x3F);
    ssd1306_command(SSD1306_SET_DISPLAY_OFFSET); ssd1306_command(0x00);
    ssd1306_command(SSD1306_SET_START_LINE);
    ssd1306_command(SSD1306_CHARGE_PUMP);       ssd1306_command(0x14); /* enable charge pump */
    ssd1306_command(SSD1306_SET_SEGMENT_REMAP);
    ssd1306_command(SSD1306_SET_COM_SCAN_DEC);
    ssd1306_command(SSD1306_SET_COM_PINS);     ssd1306_command(0x12);
    ssd1306_command(SSD1306_SET_CONTRAST);      ssd1306_command(0xCF);
    ssd1306_command(SSD1306_SET_PRECHARGE);     ssd1306_command(0xF1);
    ssd1306_command(SSD1306_SET_VCOM_DETECT);   ssd1306_command(0x40);
    ssd1306_command(SSD1306_SET_OSC_FREQ);     ssd1306_command(0x80);
    ssd1306_command(SSD1306_NORMAL_DISPLAY);
    ssd1306_command(0x20); /* addressing mode */
    ssd1306_command(0x00); /* horizontal addressing */
    ssd1306_command(SSD1306_DISPLAY_ON);

    delay_ms(100);
    display_clear();
    display_flush();
    display_initialized = 1;
}

void display_off(void)
{
    ssd1306_command(SSD1306_DISPLAY_OFF);
}

void display_on(void)
{
    ssd1306_command(SSD1306_DISPLAY_ON);
}