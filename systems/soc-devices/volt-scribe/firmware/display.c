/*
 * volt-scribe — display.c
 * SSD1306 128×64 OLED rendering for voltammograms, Nyquist plots, etc.
 */

#include "display.h"
#include <math.h>
#include <string.h>
#include <stdio.h>

/* ── SSD1306 I2C commands ───────────────────────────────────────── */

#define SSD1306_ADDR        0x3C
#define SSD1306_WIDTH        128
#define SSD1306_HEIGHT       64
#define SSD1306_PAGES        8

extern I2C_HandleTypeDef hi2c1;

static uint8_t framebuf[SSD1306_WIDTH * SSD1306_PAGES];

/* ── Low-level I2C ─────────────────────────────────────────────── */

static void ssd1306_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd};
    HAL_I2C_Master_Transmit(&hi2c1, SSD1306_ADDR << 1, buf, 2, 10);
}

static void ssd1306_data(uint8_t *data, int len)
{
    uint8_t prefix = 0x40;
    /* Send data with Co bit */
    HAL_I2C_Mem_Write(&hi2c1, SSD1306_ADDR << 1, 0x40,
                       I2C_MEMADD_SIZE_8BIT, data, len, 50);
}

/* ── Init ───────────────────────────────────────────────────────── */

void display_init(void)
{
    /* Reset sequence for SSD1306 */
    ssd1306_cmd(0xAE);  /* Display off */
    ssd1306_cmd(0xD5);  /* Set display clock div */
    ssd1306_cmd(0x80);
    ssd1306_cmd(0xA8);  /* Set multiplex */
    ssd1306_cmd(63);
    ssd1306_cmd(0xD3);  /* Set display offset */
    ssd1306_cmd(0x00);
    ssd1306_cmd(0x40);  /* Set start line = 0 */
    ssd1306_cmd(0x8D);  /* Enable charge pump */
    ssd1306_cmd(0x14);
    ssd1306_cmd(0x20);  /* Set memory mode = horizontal */
    ssd1306_cmd(0x00);
    ssd1306_cmd(0xA1);  /* Segment remap = 1 */
    ssd1306_cmd(0xC8);  /* COM scan direction = remapped */
    ssd1306_cmd(0xDA);  /* Set COM pins */
    ssd1306_cmd(0x12);
    ssd1306_cmd(0x81);  /* Set contrast */
    ssd1306_cmd(0xCF);
    ssd1306_cmd(0xD9);  /* Set pre-charge */
    ssd1306_cmd(0xF1);
    ssd1306_cmd(0xDB);  /* Set VCOMH deselect level */
    ssd1306_cmd(0x40);
    ssd1306_cmd(0xA4);  /* Entire display on, follow RAM */
    ssd1306_cmd(0xA6);  /* Normal display */
    ssd1306_cmd(0xAF);  /* Display on */

    memset(framebuf, 0, sizeof(framebuf));
    display_update();
}

/* ── Framebuffer operations ─────────────────────────────────────── */

void display_clear(void)
{
    memset(framebuf, 0, sizeof(framebuf));
}

void display_pixel(int x, int y, int set)
{
    if (x < 0 || x >= SSD1306_WIDTH || y < 0 || y >= SSD1306_HEIGHT) return;
    if (set)
        framebuf[x + (y / 8) * SSD1306_WIDTH] |= (1 << (y & 7));
    else
        framebuf[x + (y / 8) * SSD1306_WIDTH] &= ~(1 << (y & 7));
}

void display_line(int x0, int y0, int x1, int y1)
{
    /* Bresenham's line algorithm */
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;

    while (1) {
        display_pixel(x0, y0, 1);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

void display_update(void)
{
    ssd1306_cmd(0x21);  /* Set column address */
    ssd1306_cmd(0);
    ssd1306_cmd(127);
    ssd1306_cmd(0x22);  /* Set page address */
    ssd1306_cmd(0);
    ssd1306_cmd(7);
    ssd1306_data(framebuf, sizeof(framebuf));
}

/* ── 5×7 font (simplified) ─────────────────────────────────────── */

static const uint8_t font5x7[][5] = {
    /* Space */ {0x00,0x00,0x00,0x00,0x00},
    /* 0 */ {0x3E,0x51,0x49,0x45,0x3E},
    /* 1 */ {0x00,0x42,0x7F,0x40,0x00},
    /* 2 */ {0x42,0x61,0x51,0x49,0x46},
    /* 3 */ {0x21,0x41,0x45,0x4B,0x31},
    /* 4 */ {0x18,0x14,0x12,0x7F,0x10},
    /* 5 */ {0x27,0x45,0x45,0x45,0x39},
    /* 6 */ {0x3C,0x4A,0x49,0x49,0x30},
    /* 7 */ {0x01,0x71,0x09,0x05,0x03},
    /* 8 */ {0x36,0x49,0x49,0x49,0x36},
    /* 9 */ {0x06,0x49,0x49,0x29,0x1E},
    /* A-Z and more omitted for brevity — use uppercase only */
};

static void display_char(int x, int y, char c)
{
    if (c >= '0' && c <= '9') {
        int idx = c - '0' + 1;
        for (int col = 0; col < 5; col++) {
            for (int row = 0; row < 7; row++) {
                if (font5x7[idx][col] & (1 << row)) {
                    display_pixel(x + col, y + row, 1);
                }
            }
        }
    }
}

static void display_text(int x, int y, const char *str)
{
    while (*str) {
        display_char(x, y, *str);
        x += 6;
        str++;
    }
}

/* ── High-level display functions ───────────────────────────────── */

void display_show_splash(void)
{
    display_clear();
    display_text(16, 24, "U0LT SCR1BE");
    display_text(24, 40, "U10");
    display_update();
}

void display_show_idle(void)
{
    display_clear();
    display_text(0, 0, "U0LT SCR1BE");
    display_text(0, 16, "READ9");
    display_update();
}

void display_show_running(int mode)
{
    display_clear();
    const char *names[] = {"C0", "DP0", "SW0", "E1S", "1-t", "GAL0"};
    if (mode >= 0 && mode < 6) {
        display_text(0, 0, names[mode]);
    }
    display_text(64, 0, "RUN");
    display_update();
}

void display_show_mode(int mode)
{
    display_clear();
    const char *names[] = {"C0", "DP0", "SW0", "E1S", "1-t", "GAL0"};
    if (mode >= 0 && mode < 6) {
        display_text(0, 0, names[mode]);
    }
    display_update();
}

/* ── Plot functions ─────────────────────────────────────────────── */

static void plot_axes(int x0, int y0, int w, int h)
{
    display_line(x0, y0, x0 + w, y0);         /* X axis */
    display_line(x0, y0 - h, x0, y0);          /* Y axis */
    display_pixel(x0 + w, y0, 1);              /* X end */
    display_pixel(x0, y0 - h, 1);              /* Y end */
}

void display_plot_cv(const float *E, const float *I, int n,
                     const void *peaks, int n_peaks)
{
    display_clear();

    /* Plot area: 4,0 to 123,59 */
    int px0 = 8, py0 = 56, pw = 112, ph = 48;

    /* Find E and I ranges */
    float E_min = E[0], E_max = E[0];
    float I_min = I[0], I_max = I[0];
    for (int i = 1; i < n; i++) {
        if (E[i] < E_min) E_min = E[i];
        if (E[i] > E_max) E_max = E[i];
        if (I[i] < I_min) I_min = I[i];
        if (I[i] > I_max) I_max = I[i];
    }
    float E_range = E_max - E_min;
    float I_range = I_max - I_min;
    if (E_range < 1e-6f) E_range = 1e-6f;
    if (I_range < 1e-12f) I_range = 1e-12f;

    plot_axes(px0, py0, pw, ph);

    /* Plot data points */
    int prev_x = -1, prev_y = -1;
    for (int i = 0; i < n; i++) {
        int x = px0 + (int)((E[i] - E_min) / E_range * pw);
        int y = py0 - (int)((I[i] - I_min) / I_range * ph);
        if (x < px0) x = px0;
        if (x > px0 + pw) x = px0 + pw;
        if (y < py0 - ph) y = py0 - ph;
        if (y > py0) y = py0;

        if (prev_x >= 0) {
            display_line(prev_x, prev_y, x, y);
        }
        prev_x = x;
        prev_y = y;
    }

    display_text(0, 0, "C0");
    display_update();
}

void display_plot_dpv(const float *E, const float *dI, int n)
{
    display_clear();
    display_text(0, 0, "DP0");
    /* Simplified: show last data point */
    char buf[16];
    snprintf(buf, sizeof(buf), "%.0f", dI[n-1] * 1e6f);
    display_text(40, 0, buf);
    display_update();
}

void display_plot_swv(const float *E, const float *dI, int n)
{
    display_clear();
    display_text(0, 0, "SW0");
    display_update();
}

void display_plot_nyquist(const void *eis_data, int n)
{
    display_clear();
    display_text(0, 0, "E1S");
    display_update();
}

void display_plot_it(float t, float I)
{
    display_clear();
    display_text(0, 0, "1-t");
    display_update();
}