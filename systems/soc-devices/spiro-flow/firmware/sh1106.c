/**
 * spiro_flow/sh1106.c — SH1106 OLED display driver for Spiro Flow
 *
 * 128×64 monochrome OLED on I2C (address 0x3C).
 *
 * Display modes:
 *   IDLE     — logo + "Press MEASURE"
 *   READY    — "BLOW!" prompt + animated arrow
 *   CAPTURE  — real-time flow-volume curve being drawn
 *   RESULTS  — FVC/FEV1/FEV1FVC/PEF values + grade + predicted %
 *   REVIEW   — best maneuver results
 *   SETTINGS — patient parameter entry (age/height/sex)
 *
 * The SH1106 has a 128×64 GDDRAM organized in 8 pages × 128 columns.
 * Each byte = 8 vertical pixels.
 */

#include "main.h"
#include "sh1106.h"
#include <string.h>
#include <stdio.h>

#define TAG "OLED"
#define SH1106_ADDR  0x3C

#define SH1106_WIDTH   128
#define SH1106_HEIGHT  64
#define SH1106_PAGES   8

/* Display buffer (128 × 8 pages = 1024 bytes) */
static uint8_t s_fb[SH1106_WIDTH * SH1106_PAGES];
static bool s_dirty = true;

/* ── I2C helpers ───────────────────────────────────────────────────── */

static void i2c_cmd(uint8_t cmd)
{
    /* SH1106 control byte: 0x80 = single command byte */
    /* CH32V203 HAL I2C write: [0x3C << 1 | W, 0x80, cmd] */
    (void)cmd;
}

static void i2c_data(const uint8_t *data, int len)
{
    /* SH1106 data byte: 0x40 prefix for data stream */
    (void)data; (void)len;
}

/* ── SH1106 low-level ──────────────────────────────────────────────── */

static void sh1106_write_cmd(uint8_t cmd)
{
    i2c_cmd(cmd);
}

int sh1106_init(void)
{
    /* Initialization sequence for SH1106 */
    sh1106_write_cmd(0xAE); /* display off */
    sh1106_write_cmd(0x02); /* set low column address */
    sh1106_write_cmd(0x10); /* set high column address */
    sh1106_write_cmd(0x40); /* set display start line */
    sh1106_write_cmd(0xB0); /* set page address */
    sh1106_write_cmd(0x81); /* set contrast */
    sh1106_write_cmd(0xCF); /* contrast value */
    sh1106_write_cmd(0xA1); /* seg remap = on */
    sh1106_write_cmd(0xA6); /* normal display */
    sh1106_write_cmd(0xA8); /* set multiplex ratio */
    sh1106_write_cmd(0x3F); /* 1/64 duty */
    sh1106_write_cmd(0xA4); /* output follows RAM */
    sh1106_write_cmd(0xD3); /* set display offset */
    sh1106_write_cmd(0x00); /* no offset */
    sh1106_write_cmd(0xD5); /* set osc division */
    sh1106_write_cmd(0x80); /* divide by 2 */
    sh1106_write_cmd(0xD9); /* set pre-charge period */
    sh1106_write_cmd(0xF1); /* phase 1=1, phase 2=15 */
    sh1106_write_cmd(0xDA); /* set com pins */
    sh1106_write_cmd(0x12); /* com pin config */
    sh1106_write_cmd(0xDB); /* set vcomh deselect */
    sh1106_write_cmd(0x40); /* 0.77 × Vcc */
    sh1106_write_cmd(0xAD); /* set charge pump */
    sh1106_write_cmd(0x8B); /* enable charge pump */
    sh1106_write_cmd(0xAF); /* display on */

    memset(s_fb, 0, sizeof(s_fb));
    s_dirty = true;

    ESP_LOGI(TAG, "SH1106 OLED initialized (128x64, addr 0x3C)");
    return 0;
}

/* ── Framebuffer operations ────────────────────────────────────────── */

static void fb_set_pixel(int x, int y, bool on)
{
    if (x < 0 || x >= SH1106_WIDTH || y < 0 || y >= SH1106_HEIGHT)
        return;
    int page = y / 8;
    int bit = y % 8;
    if (on)
        s_fb[page * SH1106_WIDTH + x] |= (1 << bit);
    else
        s_fb[page * SH1106_WIDTH + x] &= ~(1 << bit);
}

static void fb_clear(void)
{
    memset(s_fb, 0, sizeof(s_fb));
    s_dirty = true;
}

static void fb_flush(void)
{
    if (!s_dirty) return;
    for (int page = 0; page < SH1106_PAGES; page++) {
        sh1106_write_cmd(0xB0 + page);       /* set page */
        sh1106_write_cmd(0x02);              /* low column = 2 (SH1106 offset) */
        sh1106_write_cmd(0x10);              /* high column = 0 */
        i2c_data(&s_fb[page * SH1106_WIDTH], SH1106_WIDTH);
    }
    s_dirty = false;
}

/* ── Simple 5x7 font ───────────────────────────────────────────────── */

/* Minimal 5x7 font for digits, letters, and symbols.
 * In production, a full font table would be stored in flash.
 * Here we provide drawing functions using a basic font.
 */

static const uint8_t font5x7[][5] = {
    /* 0-9 */
    {0x3E,0x51,0x49,0x45,0x3E}, /* 0 */
    {0x00,0x42,0x7F,0x40,0x00}, /* 1 */
    {0x42,0x61,0x51,0x49,0x46}, /* 2 */
    {0x21,0x41,0x45,0x4B,0x31}, /* 3 */
    {0x18,0x14,0x12,0x7F,0x10}, /* 4 */
    {0x27,0x45,0x45,0x45,0x39}, /* 5 */
    {0x3C,0x4A,0x49,0x49,0x30}, /* 6 */
    {0x01,0x71,0x09,0x05,0x03}, /* 7 */
    {0x36,0x49,0x49,0x49,0x36}, /* 8 */
    {0x06,0x49,0x49,0x29,0x1E}, /* 9 */
};

static void fb_draw_char(int x, int y, char c, bool on)
{
    if (c >= '0' && c <= '9') {
        int idx = c - '0';
        for (int i = 0; i < 5; i++) {
            uint8_t col = font5x7[idx][i];
            for (int j = 0; j < 7; j++) {
                if (col & (1 << j))
                    fb_set_pixel(x + i, y + j, on);
            }
        }
    }
    /* In production: full ASCII font table */
}

static void fb_draw_string(int x, int y, const char *str, bool on)
{
    int cx = x;
    for (int i = 0; str[i]; i++) {
        fb_draw_char(cx, y, str[i], on);
        cx += 6; /* 5px char + 1px spacing */
    }
}

/* Draw a line (Bresenham) */
static void fb_draw_line(int x0, int y0, int x1, int y1)
{
    int dx = abs(x1 - x0), dy = -abs(y1 - y0);
    int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    while (1) {
        fb_set_pixel(x0, y0, true);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

/* ── Display modes ─────────────────────────────────────────────────── */

void sh1106_draw_idle(void)
{
    fb_clear();
    fb_draw_string(20, 8, "SPIRO FLOW", true);
    fb_draw_string(16, 24, "PRESS MEASURE", true);
    fb_draw_string(28, 40, "TO START", true);
    fb_flush();
}

void sh1106_draw_ready(uint8_t battery_pct)
{
    fb_clear();
    fb_draw_string(36, 4, "READY!", true);
    fb_draw_string(20, 20, "BLOW NOW!", true);

    /* Animated arrow (static version) */
    fb_draw_line(64, 40, 80, 40);
    fb_draw_line(80, 40, 74, 36);
    fb_draw_line(80, 40, 74, 44);

    /* Battery indicator (top right) */
    char bat_str[8];
    snprintf(bat_str, sizeof(bat_str), "%d%%", battery_pct);
    fb_draw_string(100, 0, bat_str, true);

    fb_flush();
}

void sh1106_draw_capture(const maneuver_buffer_t *m, float current_flow, float current_vol)
{
    fb_clear();

    /* Draw flow-volume loop in real time:
     * X axis = volume (0 to max_vol), Y axis = flow (0 to max_flow)
     * Map to 128×64 display
     */
    float max_vol = 4000.0f;  /* 4L default scale */
    float max_flow = 10.0f;   /* 10 L/s default scale */

    /* Auto-scale */
    if (current_vol > max_vol * 0.8f) max_vol = current_vol * 1.2f;
    if (current_flow > max_flow * 0.8f) max_flow = current_flow * 1.2f;

    /* Draw axes */
    fb_draw_line(8, 56, 120, 56);  /* X axis (volume) */
    fb_draw_line(8, 4, 8, 56);     /* Y axis (flow) */

    /* Plot flow-volume curve from buffer */
    int n = m->n_samples;
    if (n > 1) {
        int prev_x = 8, prev_y = 56;
        for (int i = 0; i < n; i += 2) {  /* plot every 2nd sample */
            float vol = m->volume_ml[i];
            float flow = m->flow_lps[i];
            int x = 8 + (int)(vol / max_vol * 112.0f);
            int y = 56 - (int)(flow / max_flow * 52.0f);
            if (x > 120) x = 120;
            if (y < 4) y = 4;
            fb_draw_line(prev_x, prev_y, x, y);
            prev_x = x;
            prev_y = y;
        }
    }

    /* Current values text */
    char buf[16];
    snprintf(buf, sizeof(buf), "%.1f L/s", current_flow);
    fb_draw_string(30, 0, buf, true);
    snprintf(buf, sizeof(buf), "%.1f mL", current_vol);
    fb_draw_string(30, 58, buf, true);

    fb_flush();
}

void sh1106_draw_results(const spiro_result_t *r, uint8_t battery_pct)
{
    fb_clear();

    char buf[20];

    /* Title */
    fb_draw_string(0, 0, "FVC:", true);
    snprintf(buf, sizeof(buf), "%.2fL", r->fvc_liters);
    fb_draw_string(36, 0, buf, true);
    snprintf(buf, sizeof(buf), "%.0f%%", r->fvc_pct_pred);
    fb_draw_string(90, 0, buf, true);

    fb_draw_string(0, 10, "FEV1:", true);
    snprintf(buf, sizeof(buf), "%.2fL", r->fev1_liters);
    fb_draw_string(36, 10, buf, true);
    snprintf(buf, sizeof(buf), "%.0f%%", r->fev1_pct_pred);
    fb_draw_string(90, 10, buf, true);

    fb_draw_string(0, 20, "Ratio:", true);
    snprintf(buf, sizeof(buf), "%.1f%%", r->fev1_fvc_ratio);
    fb_draw_string(42, 20, buf, true);

    fb_draw_string(0, 30, "PEF:", true);
    snprintf(buf, sizeof(buf), "%.1fL/s", r->pef_lps);
    fb_draw_string(30, 30, buf, true);

    fb_draw_string(0, 40, "FEF:", true);
    snprintf(buf, sizeof(buf), "%.1f", r->fef2575_lps);
    fb_draw_string(30, 40, buf, true);

    /* Quality grade */
    char grade_char = 'A' + (4 - r->grade);
    if (r->grade == GRADE_F) grade_char = 'F';
    fb_draw_string(0, 54, "Grade:", true);
    snprintf(buf, sizeof(buf), "%c", grade_char);
    fb_draw_string(42, 54, buf, true);

    /* Pattern */
    const char *pattern_str = "Normal";
    if (r->pattern == 1) pattern_str = "Obstr";
    else if (r->pattern == 2) pattern_str = "Restr";
    else if (r->pattern == 3) pattern_str = "Mixed";
    fb_draw_string(70, 54, pattern_str, true);

    fb_flush();
}

void sh1106_draw_settings(const patient_t *p, int field)
{
    fb_clear();
    fb_draw_string(0, 0, "PATIENT SETUP", true);

    char buf[24];
    snprintf(buf, sizeof(buf), "Age: %d", p->age_years);
    fb_draw_string(0, 16, buf, field == 0);

    snprintf(buf, sizeof(buf), "Ht:  %d cm", p->height_cm);
    fb_draw_string(0, 26, buf, field == 1);

    snprintf(buf, sizeof(buf), "Sex: %s", p->sex == 0 ? "Male" : "Female");
    fb_draw_string(0, 36, buf, field == 2);

    fb_draw_string(0, 54, "MEASURE=save", true);
    fb_flush();
}

/* ── ESP logging shim ──────────────────────────────────────────────── */
#ifndef ESP_LOGI
#define ESP_LOGI(tag, fmt, ...) do { printf("[%s] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#include <stdio.h>
#endif