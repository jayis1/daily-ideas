/*
 * visco-shear / firmware / oled_display.c
 * SH1106 OLED (128×64, I2C) display driver for Visco Shear
 *
 * MIT License.
 */
#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "main.h"
#include "oled_display.h"
#include "spindle.h"

#define OLED_ADDR     0x3C
#define OLED_WIDTH    128
#define OLED_HEIGHT   64
#define OLED_PAGES    8

/* SH1106 commands */
#define SH1106_SET_CONTRAST    0x81
#define SH1106_DISPLAY_ON      0xAF
#define SH1106_DISPLAY_OFF     0xAE
#define SH1106_PAGE_ADDR       0xB0
#define SH1106_COL_LOW         0x00
#define SH1106_COL_HIGH        0x10
#define SH1106_SEG_REMAP       0xA1
#define SH1106_COM_SCAN_INV    0xC8

static uint8_t framebuffer[OLED_WIDTH * OLED_PAGES];
static bool initialized = false;

static void oled_cmd(uint8_t cmd)
{
    uint8_t buf[2] = { 0x00, cmd };
    i2c_write_blocking(i2c0, OLED_ADDR, buf, 2, false);
}

static void oled_data(uint8_t data)
{
    uint8_t buf[2] = { 0x40, data };
    i2c_write_blocking(i2c0, OLED_ADDR, buf, 2, false);
}

/* Simple 5×8 font (printable ASCII subset) */
static const uint8_t font5x8[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x5F,0x00,0x00}, /* ! */
    /* ... abbreviated; full font would have 96 entries */
};

static void oled_clear(void)
{
    memset(framebuffer, 0, sizeof(framebuffer));
}

static void oled_flush(void)
{
    for (int page = 0; page < OLED_PAGES; page++) {
        oled_cmd(SH1106_PAGE_ADDR | page);
        oled_cmd(SH1106_COL_LOW | 2);  /* Column offset for SH1106 */
        oled_cmd(SH1106_COL_HIGH | 0);
        for (int col = 0; col < OLED_WIDTH; col++) {
            oled_data(framebuffer[page * OLED_WIDTH + col]);
        }
    }
}

static void oled_set_pixel(int x, int y, bool on)
{
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;
    int page = y / 8;
    int bit = y % 8;
    if (on) framebuffer[page * OLED_WIDTH + x] |= (1 << bit);
    else    framebuffer[page * OLED_WIDTH + x] &= ~(1 << bit);
}

static void oled_draw_text(int x, int y, const char *str, int scale)
{
    /* Simplified: draw using character lookup.
     * In production, full 5x8 font table would be used. */
    (void)x; (void)y; (void)str; (void)scale;
    /* Stub: actual text rendering uses font bitmap */
}

static void oled_draw_line(int x0, int y0, int x1, int y1)
{
    int dx = abs(x1 - x0), dy = abs(y1 - y0);
    int sx = (x0 < x1) ? 1 : -1, sy = (y0 < y1) ? 1 : -1;
    int err = dx - dy;
    while (1) {
        oled_set_pixel(x0, y0, true);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x0 += sx; }
        if (e2 < dx)  { err += dx; y0 += sy; }
    }
}

void oled_display_init(void)
{
    /* Init sequence */
    oled_cmd(SH1106_DISPLAY_OFF);
    sleep_ms(10);
    oled_cmd(0x02);  /* Set display start line = 0 */
    oled_cmd(SH1106_SEG_REMAP);
    oled_cmd(SH1106_COM_SCAN_INV);
    oled_cmd(SH1106_SET_CONTRAST);
    oled_cmd(0x7F);
    oled_cmd(0x2E);  /* Deactivate scroll */
    oled_cmd(0xA4);  /* Display resume RAM */
    oled_cmd(0xA6);  /* Normal display (not inverted) */
    oled_cmd(SH1106_DISPLAY_ON);

    oled_clear();
    oled_flush();
    initialized = true;
    printf("[OLED] SH1106 initialized (0x%02X)\n", OLED_ADDR);
}

void oled_display_show_idle(measure_mode_t mode, spindle_type_t sp,
                            float temp, float vbat)
{
    if (!initialized) return;
    oled_clear();

    const char *mode_str[] = {"Flow", "Yield", "Osc", "Thixo", "Single"};
    char buf[22];

    snprintf(buf, sizeof(buf), "Visco Shear v1.0");
    oled_draw_text(0, 0, buf, 1);

    snprintf(buf, sizeof(buf), "Mode: %s", mode_str[mode]);
    oled_draw_text(0, 12, buf, 1);

    snprintf(buf, sizeof(buf), "Spndl: %s", spindle_name(sp));
    oled_draw_text(0, 22, buf, 1);

    snprintf(buf, sizeof(buf), "T: %.1f C", temp);
    oled_draw_text(0, 32, buf, 1);

    snprintf(buf, sizeof(buf), "Bat: %.1fV", vbat);
    oled_draw_text(0, 42, buf, 1);

    oled_draw_text(0, 54, "START to begin", 1);

    oled_flush();
}

void oled_display_show_status(const char *line1, const char *line2)
{
    if (!initialized) return;
    oled_clear();
    if (line1) oled_draw_text(0, 20, line1, 1);
    if (line2) oled_draw_text(0, 32, line2, 1);
    oled_flush();
}

void oled_display_show_flow_point(int step, int total, float eta, float gamma)
{
    if (!initialized) return;
    oled_clear();
    char buf[22];
    snprintf(buf, sizeof(buf), "Flow %d/%d", step, total);
    oled_draw_text(0, 0, buf, 1);
    snprintf(buf, sizeof(buf), "eta=%.1f mPa.s", eta);
    oled_draw_text(0, 16, buf, 1);
    snprintf(buf, sizeof(buf), "gd=%.2f 1/s", gamma);
    oled_draw_text(0, 28, buf, 1);

    /* Mini flow curve plot (bottom 24 rows) */
    /* Plot viscosity vs point index */
    int plot_y0 = 40, plot_h = 20;
    oled_draw_line(0, plot_y0 + plot_h, OLED_WIDTH, plot_y0 + plot_h);  /* X axis */
    for (int i = 0; i < step; i++) {
        int x = i * (OLED_WIDTH / total);
        int y = plot_y0 + plot_h - 2;
        oled_set_pixel(x, y, true);
    }

    oled_flush();
}

void oled_display_show_osc_point(int step, int total, float Gp, float Gd)
{
    if (!initialized) return;
    oled_clear();
    char buf[22];
    snprintf(buf, sizeof(buf), "Osc %d/%d", step, total);
    oled_draw_text(0, 0, buf, 1);
    snprintf(buf, sizeof(buf), "G'=%.1f Pa", Gp);
    oled_draw_text(0, 16, buf, 1);
    snprintf(buf, sizeof(buf), "G''=%.1f Pa", Gd);
    oled_draw_text(0, 28, buf, 1);
    oled_flush();
}

void oled_display_show_result(const measure_result_t *res)
{
    if (!initialized) return;
    oled_clear();
    char buf[22];

    snprintf(buf, sizeof(buf), "Result: %s", model_names[res->best_fit.model]);
    oled_draw_text(0, 0, buf, 1);

    if (res->n_points > 0) {
        float eta_avg = 0;
        for (int i = 0; i < res->n_points; i++) eta_avg += res->viscosity[i];
        eta_avg /= res->n_points;
        snprintf(buf, sizeof(buf), "eta_avg=%.1f mPa.s", eta_avg);
        oled_draw_text(0, 14, buf, 1);
    }

    snprintf(buf, sizeof(buf), "R2=%.4f", res->best_fit.r_squared);
    oled_draw_text(0, 26, buf, 1);

    if (res->n_freq > 0) {
        snprintf(buf, sizeof(buf), "G'=%.1f G''=%.1f",
                 res->G_prime[res->n_freq/2], res->G_double[res->n_freq/2]);
        oled_draw_text(0, 38, buf, 1);
    }

    if (res->hysteresis_area > 0) {
        snprintf(buf, sizeof(buf), "Thixo=%.1f", res->hysteresis_area);
        oled_draw_text(0, 50, buf, 1);
    }

    oled_flush();
}