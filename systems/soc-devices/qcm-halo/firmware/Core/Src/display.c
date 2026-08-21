/*
 * display.c — OLED SH1106 rendering for QCM Halo
 *
 * SH1106: 128×64 monochrome OLED, I2C interface, page-addressed.
 * Each page is 8 rows. Commands and data are sent via I2C.
 */

#include "main.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "display.h"
#include "i2c_util.h"

#define OLED_I2C_ADDR_W (OLED_I2C_ADDR << 1)

static uint8_t oled_buffer[OLED_WIDTH * OLED_HEIGHT / 8];

/* Font: 5x7 ASCII (subset) */
static const uint8_t font5x7[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x5F,0x00,0x00}, /* ! */
    /* ... abbreviated — full font would have 96 entries */
};

/* Send command to OLED */
static void oled_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd}; /* Co=0, D/C#=0 → command */
    HAL_I2C_Master_Transmit(&hi2c1, OLED_I2C_ADDR_W, buf, 2, 100);
}

/* Send data to OLED */
static void oled_data(uint8_t data)
{
    uint8_t buf[2] = {0x40, data}; /* Co=0, D/C#=1 → data */
    HAL_I2C_Master_Transmit(&hi2c1, OLED_I2C_ADDR_W, buf, 2, 100);
}

void display_init(void)
{
    HAL_Delay(100); /* OLED power-up */

    oled_cmd(0xAE); /* Display off */
    oled_cmd(0x02); /* Set lower column address */
    oled_cmd(0x10); /* Set higher column address */
    oled_cmd(0x40); /* Set display start line */
    oled_cmd(0xB0); /* Set page address */
    oled_cmd(0x81); /* Set contrast */
    oled_cmd(0xCF);
    oled_cmd(0xA1); /* Segment remap */
    oled_cmd(0xA6); /* Normal display */
    oled_cmd(0xA8); /* Set multiplex ratio */
    oled_cmd(0x3F); /* 1/64 duty */
    oled_cmd(0xAD); /* Set DC-DC */
    oled_cmd(0x8B);
    oled_cmd(0xC8); /* COM scan direction */
    oled_cmd(0xD3); /* Set display offset */
    oled_cmd(0x00);
    oled_cmd(0xD5); /* Set clock divide */
    oled_cmd(0x80);
    oled_cmd(0xD9); /* Set pre-charge */
    oled_cmd(0x22);
    oled_cmd(0xDA); /* Set COM pins */
    oled_cmd(0x12);
    oled_cmd(0xDB); /* Set VCOM deselect */
    oled_cmd(0x40);
    oled_cmd(0xAF); /* Display on */

    display_clear();
    display_update();
}

void display_clear(void)
{
    memset(oled_buffer, 0, sizeof(oled_buffer));
}

void display_update(void)
{
    for (uint8_t page = 0; page < 8; page++) {
        oled_cmd(0xB0 + page);       /* Set page */
        oled_cmd(0x02);              /* Lower column */
        oled_cmd(0x10);              /* Higher column */
        for (uint8_t col = 0; col < OLED_WIDTH; col++) {
            oled_data(oled_buffer[page * OLED_WIDTH + col]);
        }
    }
}

/* Simple 5x7 text rendering using built-in font.
 * For brevity, we use a minimal font lookup.
 * In the real implementation, a full 96-character ASCII font is included.
 */
static const uint8_t ascii_font[96][5] = {
    {0x00,0x00,0x00,0x00,0x00},{0x00,0x00,0x5F,0x00,0x00},{0x00,0x07,0x00,0x07,0x00},
    {0x14,0x7F,0x14,0x7F,0x14},{0x24,0x2A,0x7F,0x2A,0x12},{0x23,0x13,0x08,0x64,0x62},
    {0x36,0x49,0x55,0x22,0x50},{0x00,0x05,0x03,0x00,0x00},{0x00,0x1C,0x22,0x41,0x00},
    {0x00,0x41,0x22,0x1C,0x00},{0x14,0x08,0x3E,0x08,0x14},{0x08,0x08,0x3E,0x08,0x08},
    {0x00,0x50,0x30,0x00,0x00},{0x08,0x08,0x08,0x08,0x08},{0x00,0x60,0x60,0x00,0x00},
    {0x20,0x10,0x08,0x04,0x02},{0x3E,0x51,0x49,0x45,0x3E},{0x00,0x42,0x7F,0x40,0x00},
    {0x42,0x61,0x51,0x49,0x46},{0x21,0x41,0x45,0x4B,0x31},{0x18,0x14,0x12,0x7F,0x10},
    {0x27,0x45,0x45,0x45,0x39},{0x3C,0x4A,0x49,0x49,0x30},{0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36},{0x06,0x49,0x49,0x29,0x1E},{0x00,0x36,0x36,0x00,0x00},
    {0x00,0x56,0x36,0x00,0x00},{0x00,0x08,0x14,0x22,0x41},{0x14,0x14,0x14,0x14,0x14},
    {0x00,0x41,0x22,0x14,0x08},{0x02,0x01,0x51,0x09,0x06},{0x32,0x49,0x79,0x41,0x3E},
    {0x7E,0x11,0x11,0x11,0x7E},{0x7F,0x49,0x49,0x49,0x36},{0x3E,0x41,0x41,0x41,0x22},
    {0x7F,0x41,0x41,0x22,0x1C},{0x7F,0x49,0x49,0x49,0x41},{0x7F,0x09,0x09,0x01,0x01},
    {0x3E,0x41,0x41,0x51,0x32},{0x7F,0x08,0x08,0x08,0x7F},{0x00,0x41,0x7F,0x41,0x00},
    {0x20,0x40,0x41,0x3F,0x01},{0x7F,0x08,0x14,0x22,0x41},{0x7F,0x40,0x40,0x40,0x40},
    {0x7F,0x02,0x04,0x02,0x7F},{0x7F,0x04,0x08,0x10,0x7F},{0x3E,0x41,0x41,0x41,0x3E},
    {0x7F,0x09,0x09,0x09,0x06},{0x3E,0x41,0x51,0x21,0x5E},{0x7F,0x09,0x19,0x29,0x46},
    {0x46,0x49,0x49,0x49,0x31},{0x01,0x01,0x7F,0x01,0x01},{0x3F,0x41,0x41,0x41,0x3F},
    {0x1F,0x20,0x40,0x20,0x1F},{0x3F,0x40,0x38,0x40,0x3F},{0x63,0x14,0x08,0x14,0x63},
    {0x03,0x04,0x78,0x04,0x03},{0x61,0x51,0x49,0x45,0x43},{0x00,0x7F,0x41,0x41,0x00},
    {0x02,0x04,0x08,0x10,0x20},{0x00,0x41,0x41,0x7F,0x00},{0x04,0x02,0x01,0x02,0x04},
    {0x40,0x40,0x40,0x40,0x40},{0x00,0x02,0x04,0x08,0x00},{0x20,0x54,0x54,0x54,0x78},
    {0x7F,0x28,0x44,0x44,0x38},{0x38,0x44,0x44,0x44,0x20},{0x38,0x44,0x44,0x28,0x7F},
    {0x38,0x54,0x54,0x54,0x18},{0x08,0x7E,0x09,0x01,0x02},{0x08,0x14,0x54,0x3C,0x1C},
    {0x7F,0x08,0x04,0x04,0x78},{0x00,0x44,0x7D,0x40,0x00},{0x20,0x40,0x44,0x3D,0x00},
    {0x7F,0x10,0x28,0x44,0x00},{0x00,0x41,0x7F,0x40,0x00},{0x7C,0x04,0x18,0x04,0x78},
    {0x7C,0x08,0x04,0x04,0x78},{0x38,0x44,0x44,0x44,0x38},{0x7C,0x14,0x14,0x14,0x08},
    {0x08,0x14,0x14,0x18,0x7C},{0x7C,0x08,0x04,0x04,0x08},{0x48,0x54,0x54,0x54,0x20},
    {0x04,0x3F,0x44,0x40,0x20},{0x3C,0x40,0x40,0x20,0x7C},{0x1C,0x20,0x40,0x20,0x1C},
    {0x3C,0x40,0x30,0x40,0x3C},{0x44,0x28,0x10,0x28,0x44},{0x4C,0x90,0x90,0x90,0x7C},
    {0x44,0x64,0x54,0x4C,0x44},{0x00,0x08,0x36,0x41,0x00},{0x00,0x00,0x7F,0x00,0x00},
    {0x00,0x41,0x36,0x08,0x00},{0x02,0x01,0x02,0x04,0x02}
};

static void draw_char(uint8_t x, uint8_t y, char c)
{
    if (c < 32 || c > 127) c = '?';
    uint8_t idx = c - 32;
    for (uint8_t i = 0; i < 5; i++) {
        uint8_t col = ascii_font[idx][i];
        for (uint8_t j = 0; j < 7; j++) {
            if (col & (1 << j)) {
                uint16_t px = x + i;
                uint16_t py = y + j;
                if (px < OLED_WIDTH && py < OLED_HEIGHT) {
                    oled_buffer[px + (py / 8) * OLED_WIDTH] |= (1 << (py & 7));
                }
            }
        }
    }
}

void display_text(uint8_t x, uint8_t y, const char *str, uint8_t size)
{
    (void)size; /* size not implemented — always 5x7 */
    uint8_t cx = x;
    while (*str && cx < OLED_WIDTH - 5) {
        draw_char(cx, y, *str);
        cx += 6;
        str++;
    }
}

void display_pixel(uint8_t x, uint8_t y, uint8_t on)
{
    if (x >= OLED_WIDTH || y >= OLED_HEIGHT) return;
    if (on)
        oled_buffer[x + (y / 8) * OLED_WIDTH] |= (1 << (y & 7));
    else
        oled_buffer[x + (y / 8) * OLED_WIDTH] &= ~(1 << (y & 7));
}

void display_line(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1)
{
    int dx = (x1 > x0) ? x1 - x0 : x0 - x1;
    int dy = (y1 > y0) ? y1 - y0 : y0 - y1;
    int sx = (x0 < x1) ? 1 : -1;
    int sy = (y0 < y1) ? 1 : -1;
    int err = dx - dy;
    while (1) {
        display_pixel(x0, y0, 1);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x0 += sx; }
        if (e2 < dx)  { err += dx; y0 += sy; }
    }
}

void display_hline(uint8_t x, uint8_t y, uint8_t w)
{
    for (uint8_t i = 0; i < w && x + i < OLED_WIDTH; i++)
        display_pixel(x + i, y, 1);
}

void display_vline(uint8_t x, uint8_t y, uint8_t h)
{
    for (uint8_t i = 0; i < h && y + i < OLED_HEIGHT; i++)
        display_pixel(x, y + i, 1);
}

void display_rect(uint8_t x, uint8_t y, uint8_t w, uint8_t h)
{
    display_hline(x, y, w);
    display_hline(x, y + h - 1, w);
    display_vline(x, y, h);
    display_vline(x + w - 1, y, h);
}

void display_set_cursor(uint8_t x, uint8_t y)
{
    (void)x; (void)y; /* placeholder */
}

/* ── Screen implementations ─────────────────────────────── */

void display_boot(const char *msg)
{
    display_clear();
    display_text(0, 0, "QCM Halo v1.0", 1);
    display_hline(0, 9, OLED_WIDTH);
    display_text(0, 16, msg, 1);
    display_update();
}

void display_idle(float temp, float vbat, uint8_t channel)
{
    char buf[24];
    display_clear();
    display_text(0, 0, "QCM Halo", 1);
    display_text(80, 0, "IDLE", 1);
    display_hline(0, 9, OLED_WIDTH);

    snprintf(buf, sizeof(buf), "Ch: %d", channel + 1);
    display_text(0, 14, buf, 1);

    snprintf(buf, sizeof(buf), "T: %.2f C", temp);
    display_text(0, 24, buf, 1);

    snprintf(buf, sizeof(buf), "Bat: %.1fV", vbat / 1000.0f);
    display_text(0, 34, buf, 1);

    display_text(0, 48, "A:menu B:sel", 1);
    display_update();
}

void display_menu(uint8_t item)
{
    char buf[24];
    display_clear();
    display_text(0, 0, "Menu", 1);
    display_hline(0, 9, OLED_WIDTH);

    /* Show 5 items at a time, highlight current */
    uint8_t start = (item > 3) ? item - 3 : 0;
    for (uint8_t i = 0; i < 5 && (start + i) < 10; i++) {
        const char *items[] = {
            "Single Measure", "Overtone Sweep", "Calibrate",
            "Experiment", "Set Temp", "Set Pump",
            "Set Valve", "Voigt Fit", "BLE Stream", "Back"
        };
        uint8_t y = 12 + i * 10;
        if (start + i == item) {
            display_text(0, y, ">", 1);
        }
        display_text(6, y, items[start + i], 1);
    }
    (void)buf;
    display_update();
}

void display_measure_live(const qcm_result_t *r, float elapsed_s)
{
    char buf[24];
    display_clear();
    display_text(0, 0, "MEASURE", 1);
    snprintf(buf, sizeof(buf), "%.0fs", elapsed_s);
    display_text(95, 0, buf, 1);
    display_hline(0, 9, OLED_WIDTH);

    snprintf(buf, sizeof(buf), "f: %.1f Hz", r->frequency);
    display_text(0, 12, buf, 1);

    snprintf(buf, sizeof(buf), "df: %.2f Hz", r->delta_f);
    display_text(0, 22, buf, 1);

    snprintf(buf, sizeof(buf), "D: %.2e", r->dissipation);
    display_text(0, 32, buf, 1);

    snprintf(buf, sizeof(buf), "dD: %.2e", r->delta_d);
    display_text(0, 42, buf, 1);

    snprintf(buf, sizeof(buf), "mass: %.1f ng/cm2", r->sauerbrey_mass);
    display_text(0, 52, buf, 1);

    display_update();
}

void display_dissipation_plot(const uint16_t *samples, uint16_t n, float D)
{
    char buf[24];
    display_clear();
    display_text(0, 0, "Ring-Down", 1);
    display_hline(0, 9, OLED_WIDTH);

    /* Plot decay envelope (downsampled) */
    uint16_t mid = 2048;
    uint8_t plot_w = OLED_WIDTH;
    uint8_t plot_h = 48;
    uint8_t plot_y = 12;

    for (uint8_t x = 0; x < plot_w; x++) {
        uint16_t idx = (uint16_t)((uint32_t)x * n / plot_w);
        if (idx >= n) idx = n - 1;
        int32_t dev = (int32_t)samples[idx] - (int32_t)mid;
        float amp = (float)(dev < 0 ? -dev : dev);
        uint8_t y = plot_y + plot_h - (uint8_t)(amp / 2048.0f * plot_h);
        display_pixel(x, y, 1);
    }

    snprintf(buf, sizeof(buf), "D=%.3e", D);
    display_text(0, 56, buf, 1);
    display_update();
}

void display_result(const qcm_result_t *r)
{
    display_measure_live(r, 0);
}

void display_overtone_table(const overtone_sweep_t *s)
{
    char buf[24];
    display_clear();
    display_text(0, 0, "Overtone Sweep", 1);
    display_hline(0, 9, OLED_WIDTH);

    const char *labels[] = {"1st", "3rd", "5th", "7th", "9th", "11th"};
    for (uint8_t i = 0; i < QCM_OVERtones && i < 6; i++) {
        uint8_t y = 11 + i * 9;
        snprintf(buf, sizeof(buf), "%s df:%.1f", labels[i], s->delta_f[i]);
        display_text(0, y, buf, 1);
    }
    display_update();
}

void display_voigt_result(const voigt_params_t *v)
{
    char buf[24];
    display_clear();
    display_text(0, 0, "Voigt Fit", 1);
    display_hline(0, 9, OLED_WIDTH);

    snprintf(buf, sizeof(buf), "d: %.1f nm", v->thickness_nm);
    display_text(0, 12, buf, 1);

    snprintf(buf, sizeof(buf), "eta: %.1e Pa.s", v->viscosity_pa_s);
    display_text(0, 22, buf, 1);

    snprintf(buf, sizeof(buf), "mu: %.1e Pa", v->shear_mod_pa);
    display_text(0, 32, buf, 1);

    snprintf(buf, sizeof(buf), "conv: %s iter:%d",
             v->converged ? "YES" : "NO", v->iterations);
    display_text(0, 42, buf, 1);

    display_update();
}

void display_error(const char *msg)
{
    display_clear();
    display_text(0, 0, "ERROR", 1);
    display_hline(0, 9, OLED_WIDTH);
    display_text(0, 16, msg, 1);
    display_update();
}

void display_status_bar(float temp, float vbat, const char *state)
{
    char buf[24];
    snprintf(buf, sizeof(buf), "T:%.0f V:%.1f %s", temp, vbat/1000, state);
    display_text(0, 0, buf, 1);
}

void display_plot_df_dd(float *df, float *dd, uint16_t n, uint16_t current)
{
    (void)df; (void)dd; (void)n; (void)current;
    /* Implementation would plot Δf vs time and ΔD vs time */
}