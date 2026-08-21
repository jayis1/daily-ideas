/*
 * display.c — SH1106 OLED 128x64 I2C driver
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 *
 * Draws live mobility spectrum (drift-time axis), detected K0 peaks,
 * classification result (compound + class + confidence), and status bar.
 *
 * SPDX-License-Identifier: MIT
 */
#include "display.h"
#include "stm32g474_conf.h"
#include "stm32g4xx_hal.h"
#include <string.h>
#include <stdio.h>

extern I2C_HandleTypeDef hi2c1;

#define OLED_ADDR (0x3C << 1)
static uint8_t g_buf[8][128];

static void oled_cmd(uint8_t c)
{
    uint8_t b[2] = { 0x00, c };
    HAL_I2C_Master_Transmit(&hi2c1, OLED_ADDR, b, 2, 10);
}
static void oled_data(uint8_t d)
{
    uint8_t b[2] = { 0x40, d };
    HAL_I2C_Master_Transmit(&hi2c1, OLED_ADDR, b, 2, 10);
}

void display_init(void)
{
    HAL_Delay(50);
    oled_cmd(0xAE);             /* display off */
    oled_cmd(0xD5); oled_cmd(0x80); /* clock divide */
    oled_cmd(0xA8); oled_cmd(0x3F); /* mux 1/64 */
    oled_cmd(0xD3); oled_cmd(0x00); /* display offset */
    oled_cmd(0x40);             /* start line */
    oled_cmd(0x8D); oled_cmd(0x14); /* charge pump on */
    oled_cmd(0x20); oled_cmd(0x00); /* addr mode horizontal */
    oled_cmd(0xA1);             /* seg remap */
    oled_cmd(0xC8);             /* com scan dec */
    oled_cmd(0xDA); oled_cmd(0x12); /* com pins */
    oled_cmd(0x81); oled_cmd(0xCF); /* contrast */
    oled_cmd(0xD9); oled_cmd(0xF1); /* precharge */
    oled_cmd(0xDB); oled_cmd(0x40); /* vcomh */
    oled_cmd(0xA4); oled_cmd(0xA6); /* normal display */
    oled_cmd(0xAF);             /* display on */
    display_clear();
}

void display_clear(void)
{
    memset(g_buf, 0, sizeof(g_buf));
    for (int p = 0; p < 8; p++) {
        oled_cmd(0xB0 + p);
        oled_cmd(0x00); oled_cmd(0x10);
        for (int c = 0; c < 128; c++) oled_data(g_buf[p][c]);
    }
}

void display_splash(void)
{
    display_clear();
    /* simple text via 5x7 font would go here; abbreviated */
}

static void draw_pixel(int x, int y, int on)
{
    if (x < 0 || x >= 128 || y < 0 || y >= 64) return;
    int p = y / 8;
    if (on) g_buf[p][x] |=  (1 << (y & 7));
    else    g_buf[p][x] &= ~(1 << (y & 7));
}

static void draw_text(int x, int y, const char *s)
{
    /* stub: real font rendering omitted for brevity */
    (void)x; (void)y; (void)s;
}

void display_spectrum(const ims_result_t *r, const classify_result_t *cls)
{
    display_clear();
    /* draw spectrum along bottom 48 px of screen */
    int16_t base = 0;
    int16_t maxv = 1;
    for (int i = 0; i < IMS_SAMPLES_PER_SWEEP; i++) {
        int16_t v = r->spectrum[i];
        if (v > maxv) maxv = v;
    }
    for (int x = 0; x < 128; x++) {
        int idx = (int)((float)x / 128.0f * IMS_SAMPLES_PER_SWEEP);
        if (idx >= IMS_SAMPLES_PER_SWEEP) idx = IMS_SAMPLES_PER_SWEEP - 1;
        int h = (int)((float)(r->spectrum[idx] - base) / (float)(maxv - base + 1) * 48.0f);
        if (h < 0) h = 0; if (h > 48) h = 48;
        for (int y = 0; y < h; y++) draw_pixel(x, 63 - y, 1);
    }
    /* mark peaks */
    for (int i = 0; i < r->num_peaks; i++) {
        int x = (int)((r->peaks[i].drift_ms - IMS_T_START_MS) / (IMS_T_END_MS - IMS_T_START_MS) * 128.0f);
        for (int y = 52; y < 64; y++) draw_pixel(x, y, 0);
        draw_pixel(x, 63, 1); draw_pixel(x, 62, 1);
    }
    /* text: compound + confidence */
    char line[24];
    snprintf(line, sizeof(line), "%s %.0f%%", cls->name, cls->confidence * 100.0f);
    draw_text(0, 0, line);
    snprintf(line, sizeof(line), "K0=%.2f", cls->k0);
    draw_text(0, 8, line);
    snprintf(line, sizeof(line), "P=%dkPa T=%.1fC", (int)r->pressure_kpa, r->drift_temp_c);
    draw_text(0, 16, line);

    /* flush to OLED */
    for (int p = 0; p < 8; p++) {
        oled_cmd(0xB0 + p);
        oled_cmd(0x00); oled_cmd(0x10);
        for (int c = 0; c < 128; c++) oled_data(g_buf[p][c]);
    }
}

void display_status(const char *status, float hv_v, float batt_v, float p_kpa, float t_c)
{
    display_clear();
    char line[24];
    draw_text(0, 0, status);
    snprintf(line, sizeof(line), "HV=%.0fV", hv_v); draw_text(0, 10, line);
    snprintf(line, sizeof(line), "BAT=%.2fV", batt_v); draw_text(0, 20, line);
    snprintf(line, sizeof(line), "P=%.0fkPa T=%.1f", p_kpa, t_c); draw_text(0, 30, line);
    for (int p = 0; p < 8; p++) {
        oled_cmd(0xB0 + p); oled_cmd(0x00); oled_cmd(0x10);
        for (int c = 0; c < 128; c++) oled_data(g_buf[p][c]);
    }
}

void display_idle(void) { display_status("IDLE", 0, 0, 0, 0); }
void display_fault(const char *msg) { display_status(msg, 0, 0, 0, 0); }