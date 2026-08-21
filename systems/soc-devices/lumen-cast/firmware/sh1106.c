/**
 * lumen_cast/firmware/sh1106.c — SH1106 OLED display driver
 *
 * SH1106: 128×64 monochrome OLED, I2C interface, address 0x3C
 * Page-addressed: 8 pages of 128×8 pixels each.
 *
 * Display modes for Lumen Cast:
 *   - idle: logo + scan type + battery
 *   - scanning: progress bar + current angle + live polar plot
 *   - results: photometric report (flux, beam, CCT)
 *   - polar: polar plot of luminous intensity distribution
 */

#include "main.h"
#include <string.h>
#include <math.h>
#include <stdio.h>

#define TAG "OLED"
#define OLED_ADDR  SH1106_I2C_ADDR
#define OLED_WIDTH  128
#define OLED_HEIGHT 64
#define OLED_PAGES  8

/* Display buffer: 128 × 8 pages = 1024 bytes */
static uint8_t s_fb[OLED_WIDTH * OLED_PAGES];
static bool s_dirty = true;

/* ── Low-level I2C commands ────────────────────────────────────────── */

static void oled_cmd(uint8_t cmd)
{
    uint8_t buf[2] = { 0x00, cmd };  /* 0x00 = command stream */
    i2c_write_burst(OLED_ADDR, 0x00, buf + 1, 1);
}

static void oled_cmd2(uint8_t a, uint8_t b)
{
    oled_cmd(a);
    oled_cmd(b);
}

/* ── Framebuffer operations ────────────────────────────────────────── */

static void fb_clear(void)
{
    memset(s_fb, 0, sizeof(s_fb));
    s_dirty = true;
}

static void fb_set_pixel(int x, int y, bool on)
{
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;
    int page = y / 8;
    int bit = y % 8;
    if (on)
        s_fb[page * OLED_WIDTH + x] |= (1 << bit);
    else
        s_fb[page * OLED_WIDTH + x] &= ~(1 << bit);
    s_dirty = true;
}

static void fb_draw_text(int x, int y, const char *str, bool big)
{
    /* Simple 5×7 font for small, 8×16 for big (simplified) */
    extern const uint8_t font5x7[][5];
    extern const uint8_t font8x16[][16];

    int cx = x;
    for (const char *p = str; *p; p++) {
        char c = *p;
        if (c < 32 || c > 127) c = '?';

        if (big) {
            const uint8_t *glyph = font8x16[c - 32];
            for (int i = 0; i < 8; i++) {
                for (int j = 0; j < 16; j++) {
                    bool on = (glyph[j] >> (7 - i)) & 1;
                    fb_set_pixel(cx + i, y + j, on);
                }
            }
            cx += 9;
        } else {
            const uint8_t *glyph = font5x7[c - 32];
            for (int i = 0; i < 5; i++) {
                uint8_t col = glyph[i];
                for (int j = 0; j < 7; j++) {
                    bool on = (col >> j) & 1;
                    fb_set_pixel(cx + i, y + j, on);
                }
            }
            cx += 6;
        }
    }
}

static void fb_draw_line(int x0, int y0, int x1, int y1)
{
    /* Bresenham line */
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy, e2;
    while (1) {
        fb_set_pixel(x0, y0, true);
        if (x0 == x1 && y0 == y1) break;
        e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

static void fb_draw_rect(int x, int y, int w, int h, bool fill)
{
    if (fill) {
        for (int i = x; i < x + w; i++)
            for (int j = y; j < y + h; j++)
                fb_set_pixel(i, j, true);
    } else {
        fb_draw_line(x, y, x + w - 1, y);
        fb_draw_line(x, y + h - 1, x + w - 1, y + h - 1);
        fb_draw_line(x, y, x, y + h - 1);
        fb_draw_line(x + w - 1, y, x + w - 1, y + h - 1);
    }
}

static void fb_flush(void)
{
    if (!s_dirty) return;
    for (int page = 0; page < OLED_PAGES; page++) {
        oled_cmd2(0xB0 + page, 0x00);  /* set page + low col */
        oled_cmd(0x10);                 /* high col = 0 */
        /* Write 128 bytes of page data */
        i2c_write_burst_data(OLED_ADDR, 0x40, &s_fb[page * OLED_WIDTH], OLED_WIDTH);
    }
    s_dirty = false;
}

/* ── Display mode functions ────────────────────────────────────────── */

static const char *scan_type_name(scan_type_t t)
{
    switch (t) {
    case SCAN_TYPE_A:    return "Type A (360 az)";
    case SCAN_TYPE_C:    return "Type C (2D)";
    case SCAN_MERIDIAN:  return "Meridian (el cut)";
    case SCAN_NEARFIELD: return "Near-field (5deg)";
    }
    return "?";
}

void sh1106_draw_idle(void)
{
    fb_clear();
    fb_draw_text(0, 0, "LUMEN CAST", true);
    fb_draw_text(0, 16, "Goniophotometer", false);
    fb_draw_text(0, 28, "Ready to scan", false);

    char buf[24];
    extern scan_config_t s_config;  /* not directly visible; simplify */
    snprintf(buf, sizeof(buf), "Scan: %s", scan_type_name(SCAN_TYPE_C));
    fb_draw_text(0, 40, buf, false);

    snprintf(buf, sizeof(buf), "Batt: %d%%", battery_read_pct());
    fb_draw_text(0, 52, buf, false);

    fb_flush();
}

void sh1106_draw_scanning(const scan_buffer_t *s, float az, float el,
                           uint8_t batt)
{
    fb_clear();
    fb_draw_text(0, 0, "SCANNING", true);

    char buf[24];
    snprintf(buf, sizeof(buf), "Az: %.1f deg  El: %.1f deg", az, el);
    fb_draw_text(0, 14, buf, false);

    /* Progress bar */
    int progress = s->n_samples;
    int total = s->config.az_steps * s->config.el_steps;
    if (total < 1) total = 1;
    int bar_w = (progress * 100) / total;
    fb_draw_rect(0, 26, 100, 6, false);
    fb_draw_rect(1, 27, bar_w, 4, true);

    snprintf(buf, sizeof(buf), "%d/%d samples", progress, total);
    fb_draw_text(0, 36, buf, false);

    /* Mini polar plot (azimuth only, last row) */
    int cx = 64, cy = 52, r = 10;
    fb_draw_line(cx - r, cy, cx + r, cy);  /* horizontal axis */
    fb_draw_line(cx, cy - r, cx, cy + r);  /* vertical axis */

    /* Plot last few samples as polar */
    int start = s->n_samples - 36;
    if (start < 0) start = 0;
    for (int i = start; i < s->n_samples; i++) {
        float a = s->samples[i].azimuth_deg * 0.01745f;
        float I = s->samples[i].candela;
        /* Normalize to max 1 */
        float rr = (I > 1000) ? 1.0f : I / 1000.0f;
        if (rr > 1) rr = 1;
        int px = cx + (int)(rr * r * cosf(a));
        int py = cy + (int)(rr * r * sinf(a));
        fb_set_pixel(px, py, true);
    }

    fb_flush();
}

void sh1106_draw_results(const photo_result_t *r, uint8_t batt)
{
    fb_clear();
    fb_draw_text(0, 0, "RESULTS", true);

    char buf[24];
    snprintf(buf, sizeof(buf), "Flux: %.0f lm", r->luminous_flux_lm);
    fb_draw_text(0, 14, buf, false);

    snprintf(buf, sizeof(buf), "Peak: %.0f cd", r->peak_candela);
    fb_draw_text(0, 24, buf, false);

    snprintf(buf, sizeof(buf), "Beam: %.1f deg", r->beam_angle_fwhm);
    fb_draw_text(0, 34, buf, false);

    snprintf(buf, sizeof(buf), "CCT: %.0fK  Duv:%.3f", r->cct_onaxis_k,
             r->duv_onaxis);
    fb_draw_text(0, 44, buf, false);

    snprintf(buf, sizeof(buf), "Batt:%d%%  Throw:%.0fm", batt, r->throw_m);
    fb_draw_text(0, 56, buf, false);

    fb_flush();
}

void sh1106_draw_polar(const scan_buffer_t *s)
{
    /* Full-screen polar plot of luminous intensity (equator slice) */
    fb_clear();
    fb_draw_text(0, 0, "POLAR", false);

    int cx = 64, cy = 36, max_r = 28;

    /* Draw concentric circles (grid) */
    for (int r = 8; r <= max_r; r += 8) {
        for (float a = 0; a < 6.283f; a += 0.1f) {
            int px = cx + (int)(r * cosf(a));
            int py = cy + (int)(r * sinf(a));
            fb_set_pixel(px, py, true);
        }
    }

    /* Find peak for normalization */
    float max_I = 0;
    for (int i = 0; i < s->n_samples; i++)
        if (s->samples[i].candela > max_I) max_I = s->samples[i].candela;
    if (max_I < 0.01f) max_I = 1;

    /* Plot intensity as polar curve */
    int prev_x = cx, prev_y = cy;
    for (int i = 0; i < s->n_samples; i++) {
        float az = s->samples[i].azimuth_deg * 0.01745f;
        float I = s->samples[i].candela / max_I;
        int rr = (int)(I * max_r);
        int px = cx + (int)(rr * cosf(az));
        int py = cy + (int)(rr * sinf(az));
        if (i > 0) fb_draw_line(prev_x, prev_y, px, py);
        prev_x = px; prev_y = py;
    }

    fb_flush();
}

void sh1106_draw_settings(const scan_config_t *c, int field)
{
    fb_clear();
    fb_draw_text(0, 0, "SETTINGS", true);

    char buf[24];
    snprintf(buf, sizeof(buf), "Type: %s", scan_type_name(c->type));
    fb_draw_text(0, 16, buf, field == 0);

    snprintf(buf, sizeof(buf), "Az steps: %d", c->az_steps);
    fb_draw_text(0, 28, buf, field == 1);

    snprintf(buf, sizeof(buf), "El steps: %d", c->el_steps);
    fb_draw_text(0, 40, buf, field == 2);

    fb_draw_text(0, 56, "SCAN=start  MODE=next", false);
    fb_flush();
}

int sh1106_init(void)
{
    /* Init sequence for SH1106 */
    oled_cmd(0xAE);       /* display off */
    oled_cmd(0x02);       /* set lower column address */
    oled_cmd(0x10);       /* set higher column address */
    oled_cmd(0x40);       /* set display start line */
    oled_cmd(0xB0);       /* set page address */
    oled_cmd(0x81);       /* contrast control */
    oled_cmd(0xCF);       /* contrast value */
    oled_cmd(0xA1);       /* segment remap (A0=normal, A1=reverse) */
    oled_cmd(0xA6);       /* normal display (A6) / reverse (A7) */
    oled_cmd(0xA8);       /* multiplex ratio */
    oled_cmd(0x3F);       /* 1/64 duty */
    oled_cmd(0xA4);       /* output RAM content */
    oled_cmd(0xD3);       /* set display offset */
    oled_cmd(0x00);       /* offset = 0 */
    oled_cmd(0xD5);       /* set osc division */
    oled_cmd(0x80);       /* default */
    oled_cmd(0xD9);       /* set pre-charge period */
    oled_cmd(0xF1);       /* default */
    oled_cmd(0xDA);       /* set com pins */
    oled_cmd(0x12);       /* default */
    oled_cmd(0xDB);       /* set VCOM deselect */
    oled_cmd(0x40);       /* default */
    oled_cmd(0xAD);       /* set charge pump */
    oled_cmd(0x8B);       /* enable charge pump */
    oled_cmd(0xAF);       /* display ON */

    delay_ms(100);
    fb_clear();
    fb_flush();

    LOGI(TAG, "SH1106 OLED initialized (128x64, I2C 0x3C)");
    return 0;
}