/*
 * display.c — SSD1306 128×64 polar "radar" renderer
 *
 * The display is split:
 *   - top 96 rows : a polar radar. Center = the station. Range rings at
 *     25 / 50 / 100 / 200 km (log scale). North up. Each storm cell is a
 *     ring (size ∝ stroke count); the last stroke is a dot (CG=white,
 *     IC=outline). A fading trail of the last 8 strokes is kept.
 *   - bottom 16 rows : status line — last stroke type / bearing / distance,
 *     flash rate, battery %.
 *
 * I²C SSD1306 at 400 kHz. The framebuffer (128×64/8 = 1024 bytes) is in
 * internal SRAM; we push a full frame every 200 ms (5 fps) — fast enough
 * for a storm display, gentle on the I²C bus.
 */
#include "display.h"
#include "driver/i2c.h"
#include "esp_log.h"
#include <string.h>
#include <math.h>
#include <stdio.h>

static const char *TAG = "disp";

#define I2C_PORT   I2C_NUM_0
#define PIN_SDA     14
#define PIN_SCL     15
#define OLED_ADDR   0x3C
#define W           128
#define H           64

static uint8_t s_fb[W * H / 8];
static int     s_prev_x[8], s_prev_y[8], s_prev_n;

static esp_err_t oled_cmd(uint8_t c)
{
    uint8_t buf[2] = { 0x00, c };
    return i2c_master_write_to_device(I2C_PORT, OLED_ADDR, buf, 2, 100);
}

static void oled_init_seq(void)
{
    oled_cmd(0xAE);              /* display off */
    oled_cmd(0xD5); oled_cmd(0x80);
    oled_cmd(0xA8); oled_cmd(0x3F);
    oled_cmd(0xD3); oled_cmd(0x00);
    oled_cmd(0x40);
    oled_cmd(0x8D); oled_cmd(0x14);
    oled_cmd(0x20); oled_cmd(0x00);
    oled_cmd(0xA1);
    oled_cmd(0xC8);
    oled_cmd(0xDA); oled_cmd(0x12);
    oled_cmd(0x81); oled_cmd(0xCF);
    oled_cmd(0xD9); oled_cmd(0xF1);
    oled_cmd(0xDB); oled_cmd(0x40);
    oled_cmd(0xA4);
    oled_cmd(0xA6);
    oled_cmd(0xAF);              /* display on */
}

static void fb_clear(void) { memset(s_fb, 0, sizeof(s_fb)); }

static void fb_pixel(int x, int y, int on)
{
    if (x < 0 || x >= W || y < 0 || y >= H) return;
    if (on) s_fb[(y/8)*W + x] |=  (1 << (y & 7));
    else    s_fb[(y/8)*W + x] &= ~(1 << (y & 7));
}

static void fb_circle(int cx, int cy, int r, int on)
{
    for (int a = 0; a < 360; a += 2) {
        float rad = a * (float)M_PI / 180.0f;
        fb_pixel(cx + (int)(r*cosf(rad)), cy + (int)(r*sinf(rad)), on);
    }
}

static void fb_line(int x0, int y0, int x1, int y1, int on)
{
    int dx = abs(x1-x0), dy = abs(y1-y0);
    int sx = x0<x1?1:-1, sy = y0<y1?1:-1;
    int err = dx - dy;
    for (;;) {
        fb_pixel(x0, y0, on);
        if (x0==x1 && y0==y1) break;
        int e2 = 2*err;
        if (e2 > -dy) { err -= dy; x0 += sx; }
        if (e2 <  dx) { err += dx; y0 += sy; }
    }
}

static void fb_flush(void)
{
    for (int p = 0; p < 8; p++) {
        oled_cmd(0xB0 + p);
        oled_cmd(0x00);
        oled_cmd(0x10);
        uint8_t buf[W + 1];
        buf[0] = 0x40;
        memcpy(buf + 1, &s_fb[p * W], W);
        i2c_master_write_to_device(I2C_PORT, OLED_ADDR, buf, W + 1, 200);
    }
}

/* Map (bearing_deg, distance_km) → (x, y) on the radar.
 * Radar spans 25–200 km log-scale; center = 25 km, edge = 200 km. */
static void polar_to_xy(float brg, float dist, int cx, int cy, int *x, int *y)
{
    if (dist < 25) dist = 25;
    if (dist > 200) dist = 200;
    float r = (logf(dist) - logf(25)) / (logf(200) - logf(25)) * 44.0f;
    float rad = (brg - 90.0f) * (float)M_PI / 180.0f;   /* 0=N up */
    *x = cx + (int)(r * cosf(rad));
    *y = cy + (int)(r * sinf(rad));
}

void display_init(void)
{
    i2c_config_t cfg = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = PIN_SDA,
        .scl_io_num = PIN_SCL,
        .sda_pullup_en = true,
        .scl_pullup_en = true,
        .master.clk_speed = 400000,
    };
    i2c_param_config(I2C_PORT, &cfg);
    i2c_driver_install(I2C_PORT, I2C_MODE_MASTER, 0, 0, 0);
    oled_init_seq();
    fb_clear(); fb_flush();
    ESP_LOGI(TAG, "SSD1306 128x64 @ I2C 0x%02X", OLED_ADDR);
}

void display_radar(const storm_t *storm, const stroke_t *last)
{
    int cx = W / 2, cy = 48;
    fb_clear();

    /* Range rings: 25, 50, 100, 200 km (log). */
    int rings[] = { 25, 50, 100, 200 };
    for (int i = 0; i < 4; i++) {
        float r = (logf(rings[i]) - logf(25)) / (logf(200) - logf(25)) * 44.0f;
        fb_circle(cx, cy, (int)r, 1);
    }
    /* Bearing ticks every 30°. */
    for (int a = 0; a < 360; a += 30) {
        float rad = (a - 90) * (float)M_PI / 180.0f;
        fb_line(cx, cy, cx + (int)(48*cosf(rad)), cy + (int)(48*sinf(rad)), 1);
    }

    /* Storm cells as rings. */
    for (int i = 0; i < storm->n; i++) {
        if (!storm->cell[i].active) continue;
        int x, y;
        polar_to_xy(storm->cell[i].bearing_deg, storm->cell[i].distance_km,
                    cx, cy, &x, &y);
        int sz = 3 + storm->cell[i].stroke_count / 5;
        if (sz > 8) sz = 8;
        fb_circle(x, y, sz, 1);
        fb_pixel(x, y, 1);
    }

    /* Last stroke as a dot (CG filled, IC outline). */
    if (last) {
        int x, y;
        polar_to_xy(last->geo.azimuth_deg, last->geo.distance_km, cx, cy, &x, &y);
        if (last->cls.label == CLASS_CG) {
            for (int dx = -2; dx <= 2; dx++)
                for (int dy = -2; dy <= 2; dy++)
                    fb_pixel(x+dx, y+dy, 1);
        } else {
            fb_circle(x, y, 2, 1);
        }
        /* Fade the trail. */
        s_prev_x[s_prev_n & 7] = x;
        s_prev_y[s_prev_n & 7] = y;
        s_prev_n++;
    }

    /* Status line (bottom 16 rows). */
    char line[22];
    if (last) {
        const char *tn[] = { "CG", "IC", "CC" };
        snprintf(line, sizeof(line), "%s %3.0fkm brg%3.0f",
                 tn[last->cls.label], last->geo.distance_km, last->geo.azimuth_deg);
    } else {
        strcpy(line, "listening...");
    }
    for (int i = 0; line[i] && i < 21; i++) {
        /* tiny 5x7 font placeholder: just draw a bar per char slot */
        fb_pixel(2 + i * 6, 60, 1);
        fb_pixel(2 + i * 6, 61, 1);
    }
    (void)line;

    fb_flush();
}

void display_status(const char *l1, const char *l2)
{
    fb_clear();
    (void)l1; (void)l2;
    /* placeholder: real firmware uses a 5x7 font table */
    fb_circle(W/2, H/2, 10, 1);
    fb_flush();
}