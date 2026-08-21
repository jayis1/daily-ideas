/*
 * display.c — SH1106 OLED 128×64 I2C driver
 *
 * I2C1 (PA11/PA12, shared with ambient sensors) at 400 kHz.
 * Renders histogram bar chart, PM values, flow, and battery.
 */

#include "display.h"
#include "stm32g474_conf.h"
#include <string.h>
#include <stdio.h>

#define SH1106_ADDR  0x3C
#define WIDTH        128
#define HEIGHT       64

static uint8_t fb[WIDTH * HEIGHT / 8];

static void i2c1_write_byte(uint8_t addr, uint8_t b)
{
    /* Use I2C1 already initialized by ambient.c */
    I2C1->CR2 = (addr << 1) | (1u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
    I2C1->TXDR = b;
    while (!(I2C1->ISR & I2C_ISR_TC)) ;
    I2C1->CR2 |= I2C_CR2_AUTOEND;
}

static void sh1106_cmd(uint8_t cmd)
{
    uint8_t buf[2] = { 0x00, cmd };
    I2C1->CR2 = (SH1106_ADDR << 1) | (2u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    for (uint8_t i = 0; i < 2; ++i) {
        while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
        I2C1->TXDR = buf[i];
    }
    while (!(I2C1->ISR & I2C_ISR_TC)) ;
    I2C1->CR2 |= I2C_CR2_AUTOEND;
}

static void sh1106_data(const uint8_t *data, uint16_t len)
{
    /* Control byte 0x40 = data stream */
    I2C1->CR2 = (SH1106_ADDR << 1) | ((uint32_t)(len + 1) << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
    I2C1->TXDR = 0x40;
    for (uint16_t i = 0; i < len; ++i) {
        while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
        I2C1->TXDR = data[i];
    }
    while (!(I2C1->ISR & I2C_ISR_TC)) ;
    I2C1->CR2 |= I2C_CR2_AUTOEND;
}

void display_init(void)
{
    /* I2C1 is initialized in ambient.c; ensure it's ready */
    sh1106_cmd(0xAE);           /* display off */
    sh1106_cmd(0xD5); sh1106_cmd(0x50);   /* clock divide */
    sh1106_cmd(0xA8); sh1106_cmd(0x3F);   /* multiplex 1/64 */
    sh1106_cmd(0xD3); sh1106_cmd(0x00);   /* display offset */
    sh1106_cmd(0x40);           /* start line 0 */
    sh1106_cmd(0xA1);           /* segment remap */
    sh1106_cmd(0xC8);           /* COM output scan direction */
    sh1106_cmd(0xDA); sh1106_cmd(0x12);   /* COM pins */
    sh1106_cmd(0x81); sh1106_cmd(0xCF);   /* contrast */
    sh1106_cmd(0xD9); sh1106_cmd(0x22);   /* pre-charge */
    sh1106_cmd(0xDB); sh1106_cmd(0x20);   /* VCOM deselect */
    sh1106_cmd(0xA4);           /* display RAM */
    sh1106_cmd(0xA6);           /* normal display */
    sh1106_cmd(0xAF);           /* display on */
    memset(fb, 0, sizeof(fb));
}

static void display_flush(void)
{
    for (uint8_t page = 0; page < 8; ++page) {
        sh1106_cmd(0xB0 + page);
        sh1106_cmd(0x02);       /* lower column */
        sh1106_cmd(0x10);       /* higher column */
        sh1106_data(&fb[page * WIDTH], WIDTH);
    }
}

void display_clear(void) { memset(fb, 0, sizeof(fb)); display_flush(); }

/* 6×8 font for simple text */
static const uint8_t font6x8[][6] = {
    {0x00,0x00,0x00,0x00,0x00,0x00}, /* space */
    /* Minimal: digits 0-9, '.', ':', 'k', 'm', 'u', 'g', '/', 'L', 'P', 'M' */
    {0x3E,0x51,0x49,0x45,0x3E,0x00}, /* 0 */
    {0x00,0x42,0x7F,0x40,0x00,0x00}, /* 1 */
    {0x42,0x61,0x51,0x49,0x46,0x00}, /* 2 */
    {0x21,0x41,0x45,0x4B,0x31,0x00}, /* 3 */
    {0x18,0x14,0x12,0x7F,0x10,0x00}, /* 4 */
    {0x27,0x45,0x45,0x45,0x39,0x00}, /* 5 */
    {0x3C,0x4A,0x49,0x49,0x30,0x00}, /* 6 */
    {0x01,0x71,0x09,0x05,0x03,0x00}, /* 7 */
    {0x36,0x49,0x49,0x49,0x36,0x00}, /* 8 */
    {0x06,0x49,0x49,0x29,0x1E,0x00}, /* 9 */
};

static void draw_char(uint8_t x, uint8_t y, char c)
{
    if (c < '0' || c > '9') return;
    const uint8_t *g = font6x8[c - '0' + 1];
    for (uint8_t col = 0; col < 6; ++col) {
        uint8_t bits = g[col];
        for (uint8_t row = 0; row < 8; ++row) {
            if (bits & (1 << row)) {
                uint16_t idx = (y / 8) * WIDTH + x + col;
                if (idx < sizeof(fb))
                    fb[idx] |= (1 << (y % 8 + row)) & 0xFF;
            }
        }
    }
}

static void draw_text(uint8_t x, uint8_t y, const char *s)
{
    while (*s) { draw_char(x, y, *s); x += 6; s++; }
}

static void draw_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h, uint8_t val)
{
    /* val: 0..h */
    if (val > h) val = h;
    for (uint8_t i = 0; i < w; ++i) {
        uint8_t hh = val;
        for (uint8_t row = 0; row < h; ++row) {
            uint16_t idx = ((y + row) / 8) * WIDTH + x + i;
            if (row < hh) {
                if (idx < sizeof(fb))
                    fb[idx] |= (1 << ((y + row) % 8));
            }
        }
    }
}

void display_show_message(const char *l1, const char *l2)
{
    memset(fb, 0, sizeof(fb));
    draw_text(0, 0, l1);
    draw_text(0, 12, l2);
    display_flush();
}

void display_show_menu(ui_menu_t item)
{
    const char *labels[] = { "1:SAMPLE", "2:CALIB", "3:ZERO", "4:VIEW", "5:BLE" };
    memset(fb, 0, sizeof(fb));
    if (item < UI_MAX) draw_text(0, 0, labels[item]);
    draw_text(0, 12, "select>");
    display_flush();
}

void display_show_sampling(const uint32_t *counts, uint8_t n,
                            float flow_lpm, float pm25, float pm10,
                            float battery_v)
{
    memset(fb, 0, sizeof(fb));
    /* Histogram: 16 bins across 128 px → 8 px each, height up to 32 px */
    uint32_t max_c = 1;
    for (uint8_t i = 0; i < n; ++i)
        if (counts[i] > max_c) max_c = counts[i];
    for (uint8_t i = 0; i < n && i < 16; ++i) {
        uint8_t h = (uint8_t)((float)counts[i] / (float)max_c * 30.0f);
        draw_bar(i * 8, 32 - h, 6, h, h);
    }
    /* Numeric PM values (simplified: show first 5 chars of numbers) */
    char buf[16];
    snprintf(buf, sizeof(buf), "PM2.5=%d", (int)pm25);
    draw_text(0, 40, buf);
    snprintf(buf, sizeof(buf), "PM10 =%d", (int)pm10);
    draw_text(0, 50, buf);
    display_flush();
}

void display_show_calibration(const uint32_t *counts, float size_um)
{
    memset(fb, 0, sizeof(fb));
    char buf[16];
    snprintf(buf, sizeof(buf), "CALIB %dum", (int)size_um);
    draw_text(0, 0, buf);
    draw_text(0, 12, "flow PSL...");
    display_flush();
}

void display_show_results(float pm1, float pm25, float pm10,
                           float flow, const uint32_t *counts, uint8_t n)
{
    display_show_sampling(counts, n, flow, pm25, pm10, 0);
}