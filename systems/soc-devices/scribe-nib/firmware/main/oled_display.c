/*
 * oled_display.c — SSD1306 64×32 OLED display driver for Scribe Nib
 *
 * I2C interface at 0x3C. Shows last recognized character,
 * battery level, and connection status.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "oled_display.h"
#include <string.h>
#include <stdio.h>
#include "esp_log.h"
#include "driver/i2c.h"
#include "driver/gpio.h"

static const char *TAG = "oled";

#define I2C_NUM        I2C_NUM_0
#define OLED_ADDR      0x3C
#define OLED_RST_PIN   GPIO_NUM_9

/* SSD1306 commands */
#define OLED_DISPLAY_OFF          0xAE
#define OLED_DISPLAY_ON           0xAF
#define OLED_SET_DISPLAY_CLK_DIV  0xD5
#define OLED_SET_MULTIPLEX        0xA8
#define OLED_SET_DISPLAY_OFFSET   0xD3
#define OLED_SET_START_LINE       0x40
#define OLED_SET_CHARGE_PUMP      0x8D
#define OLED_SET_SEG_REMAP        0xA1
#define OLED_SET_COM_SCAN_DIR     0xC8
#define OLED_SET_COM_PINS         0xDA
#define OLED_SET_CONTRAST         0x81
#define OLED_SET_PRECHARGE        0xD9
#define OLED_SET_VCOMH           0xDB
#define OLED_SET_ENTIRE_ON       0xA5
#define OLED_SET_NORM_DISPLAY    0xA6
#define OLED_SET_MEM_ADDR_MODE   0x20
#define OLED_SET_COL_ADDR        0x21
#define OLED_SET_PAGE_ADDR       0x22

/* 64×32 display: 4 pages × 64 columns */
#define OLED_WIDTH   64
#define OLED_HEIGHT  32
#define OLED_PAGES    4

/* Framebuffer: 4 pages × 64 columns = 256 bytes */
static uint8_t framebuffer[OLED_PAGES * OLED_WIDTH];

/* 5×7 font (ASCII 32-127) */
static const uint8_t font5x7[][5] = {
    /* Space (0x20) */ {0x00, 0x00, 0x00, 0x00, 0x00},
    /* ! */ {0x00, 0x00, 0x5F, 0x00, 0x00},
    /* " */ {0x00, 0x07, 0x00, 0x07, 0x00},
    /* # */ {0x14, 0x7F, 0x14, 0x7F, 0x14},
    /* $ */ {0x24, 0x2A, 0x7F, 0x2A, 0x12},
    /* % */ {0x23, 0x13, 0x08, 0x64, 0x62},
    /* & */ {0x36, 0x49, 0x55, 0x22, 0x50},
    /* ' */ {0x00, 0x05, 0x03, 0x00, 0x00},
    /* ( */ {0x00, 0x1C, 0x22, 0x41, 0x00},
    /* ) */ {0x00, 0x41, 0x22, 0x1C, 0x00},
    /* * */ {0x14, 0x08, 0x3E, 0x08, 0x14},
    /* + */ {0x08, 0x08, 0x3E, 0x08, 0x08},
    /* , */ {0x00, 0x50, 0x30, 0x00, 0x00},
    /* - */ {0x08, 0x08, 0x08, 0x08, 0x08},
    /* . */ {0x00, 0x60, 0x60, 0x00, 0x00},
    /* / */ {0x20, 0x10, 0x08, 0x04, 0x02},
    /* 0 */ {0x3E, 0x51, 0x49, 0x45, 0x3E},
    /* 1 */ {0x00, 0x42, 0x7F, 0x40, 0x00},
    /* 2 */ {0x42, 0x61, 0x51, 0x49, 0x46},
    /* 3 */ {0x21, 0x41, 0x45, 0x4B, 0x31},
    /* 4 */ {0x18, 0x14, 0x12, 0x7F, 0x10},
    /* 5 */ {0x27, 0x45, 0x45, 0x45, 0x39},
    /* 6 */ {0x3C, 0x4A, 0x49, 0x49, 0x30},
    /* 7 */ {0x01, 0x71, 0x09, 0x05, 0x03},
    /* 8 */ {0x36, 0x49, 0x49, 0x49, 0x36},
    /* 9 */ {0x06, 0x49, 0x49, 0x29, 0x1E},
    /* : */ {0x00, 0x36, 0x36, 0x00, 0x00},
    /* ; */ {0x00, 0x56, 0x36, 0x00, 0x00},
    /* < */ {0x08, 0x14, 0x22, 0x41, 0x00},
    /* = */ {0x14, 0x14, 0x14, 0x14, 0x14},
    /* > */ {0x00, 0x41, 0x22, 0x14, 0x08},
    /* ? */ {0x02, 0x01, 0x51, 0x09, 0x06},
    /* @ */ {0x32, 0x49, 0x79, 0x41, 0x3E},
    /* A-Z (0x41-0x5A) */
    {0x7E,0x11,0x11,0x11,0x7E}, {0x7F,0x49,0x49,0x49,0x36},
    {0x3E,0x41,0x41,0x41,0x22}, {0x7F,0x41,0x41,0x22,0x1C},
    {0x7F,0x49,0x49,0x49,0x41}, {0x7F,0x09,0x09,0x09,0x01},
    {0x3E,0x41,0x49,0x49,0x3A}, {0x7F,0x08,0x08,0x08,0x7F},
    {0x00,0x41,0x7F,0x41,0x00}, {0x20,0x40,0x41,0x3F,0x01},
    {0x7F,0x08,0x14,0x22,0x41}, {0x7F,0x40,0x40,0x40,0x40},
    {0x7F,0x02,0x0C,0x02,0x7F}, {0x7F,0x04,0x08,0x10,0x7F},
    {0x3E,0x41,0x41,0x41,0x3E}, {0x7F,0x09,0x09,0x09,0x06},
    {0x3E,0x41,0x51,0x21,0x5E}, {0x7F,0x09,0x19,0x29,0x46},
    {0x26,0x49,0x49,0x49,0x32}, {0x01,0x01,0x7F,0x01,0x01},
    {0x3F,0x40,0x40,0x40,0x3F}, {0x1F,0x20,0x40,0x20,0x1F},
    {0x3F,0x40,0x38,0x40,0x3F}, {0x63,0x14,0x08,0x14,0x63},
    {0x07,0x08,0x70,0x08,0x07}, {0x61,0x51,0x49,0x45,0x43},
};

/* ---- Low-level I2C helpers ---- */

static esp_err_t oled_write_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd};  /* Control byte 0x00 = command */
    return i2c_master_write_to_device(I2C_NUM, OLED_ADDR, buf, 2, 100 / portTICK_PERIOD_MS);
}

static esp_err_t oled_write_data(const uint8_t *data, int len)
{
    /* First byte is 0x40 (data), then the actual data */
    uint8_t *buf = malloc(len + 1);
    if (!buf) return ESP_ERR_NO_MEM;
    buf[0] = 0x40;  /* Control byte 0x40 = data */
    memcpy(&buf[1], data, len);
    esp_err_t err = i2c_master_write_to_device(I2C_NUM, OLED_ADDR, buf, len + 1, 200 / portTICK_PERIOD_MS);
    free(buf);
    return err;
}

/* ---- Public API ---- */

esp_err_t oled_display_init(void)
{
    /* Hardware reset */
    gpio_config_t rst_cfg = {
        .pin_bit_mask = (1ULL << OLED_RST_PIN),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&rst_cfg);
    gpio_set_level(OLED_RST_PIN, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(OLED_RST_PIN, 1);
    vTaskDelay(pdMS_TO_TICKS(10));

    /* Init sequence for 64×32 OLED */
    oled_write_cmd(OLED_DISPLAY_OFF);
    oled_write_cmd(OLED_SET_DISPLAY_CLK_DIV); oled_write_cmd(0x80);
    oled_write_cmd(OLED_SET_MULTIPLEX);       oled_write_cmd(0x1F);  /* 1/32 duty */
    oled_write_cmd(OLED_SET_DISPLAY_OFFSET);   oled_write_cmd(0x00);
    oled_write_cmd(OLED_SET_START_LINE | 0x00);
    oled_write_cmd(OLED_SET_CHARGE_PUMP);      oled_write_cmd(0x14);  /* Enable charge pump */
    oled_write_cmd(OLED_SET_SEG_REMAP);        /* Column 127 mapped to SEG0 */
    oled_write_cmd(OLED_SET_COM_SCAN_DIR);     /* COM0-COM31 */
    oled_write_cmd(OLED_SET_COM_PINS);         oled_write_cmd(0x02);  /* Sequential COM pins */
    oled_write_cmd(OLED_SET_CONTRAST);         oled_write_cmd(0x8F);
    oled_write_cmd(OLED_SET_PRECHARGE);        oled_write_cmd(0xF1);
    oled_write_cmd(OLED_SET_VCOMH);            oled_write_cmd(0x40);
    oled_write_cmd(OLED_SET_ENTIRE_ON);        /* Output follows RAM */
    oled_write_cmd(OLED_SET_NORM_DISPLAY);     /* Non-inverted */
    oled_write_cmd(OLED_SET_MEM_ADDR_MODE);    oled_write_cmd(0x00);  /* Horizontal mode */
    oled_write_cmd(OLED_DISPLAY_ON);

    /* Clear framebuffer */
    memset(framebuffer, 0, sizeof(framebuffer));
    oled_display_flush();

    ESP_LOGI(TAG, "SSD1306 64×32 OLED initialized");
    return ESP_OK;
}

esp_err_t oled_display_clear(void)
{
    memset(framebuffer, 0, sizeof(framebuffer));
    return oled_display_flush();
}

esp_err_t oled_display_flush(void)
{
    /* Set column and page range */
    oled_write_cmd(OLED_SET_COL_ADDR);
    oled_write_cmd(0x20);   /* Column offset for 64px wide */
    oled_write_cmd(0x5F);
    oled_write_cmd(OLED_SET_PAGE_ADDR);
    oled_write_cmd(0x00);
    oled_write_cmd(OLED_PAGES - 1);

    /* Write framebuffer */
    return oled_write_data(framebuffer, sizeof(framebuffer));
}

esp_err_t oled_display_char(char c)
{
    oled_display_clear();
    /* Draw character centered on 64×32 display */
    /* Big font: each char pixel = 4 screen pixels (2x scale) */
    int font_idx = c - 0x20;
    if (font_idx < 0 || font_idx >= (int)(sizeof(font5x7) / sizeof(font5x7[0]))) {
        font_idx = 0;  /* default to space */
    }

    int start_col = 22;  /* center 5×7 scaled 2x = 10×14 in 64px */
    int start_page = 1;  /* center in 4 pages */

    for (int col = 0; col < 5; col++) {
        uint8_t col_data = font5x7[font_idx][col];
        for (int bit = 0; bit < 7; bit++) {
            if (col_data & (1 << bit)) {
                /* Draw 2×2 pixel block */
                int sx = start_col + col * 2;
                int sp = start_page + (bit * 2) / 8;
                int sb = (bit * 2) % 8;
                if (sx < OLED_WIDTH && sp < OLED_PAGES) {
                    framebuffer[sp * OLED_WIDTH + sx]     |= (1 << sb);
                    framebuffer[sp * OLED_WIDTH + sx + 1] |= (1 << sb);
                    if (sb + 1 < 8) {
                        framebuffer[sp * OLED_WIDTH + sx]     |= (1 << (sb + 1));
                        framebuffer[sp * OLED_WIDTH + sx + 1] |= (1 << (sb + 1));
                    }
                }
            }
        }
    }

    return oled_display_flush();
}

esp_err_t oled_display_glyph(char c)
{
    return oled_display_char(c);
}

esp_err_t oled_display_printf(const char *fmt, ...)
{
    char buf[16];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    oled_display_clear();

    /* Simple small text rendering */
    int x = 0;
    for (int i = 0; buf[i] && x < OLED_WIDTH - 5; i++) {
        int font_idx = buf[i] - 0x20;
        if (font_idx < 0 || font_idx >= (int)(sizeof(font5x7) / sizeof(font5x7[0])))
            font_idx = 0;

        for (int col = 0; col < 5; col++) {
            uint8_t cd = font5x7[font_idx][col];
            if (x + col < OLED_WIDTH) {
                framebuffer[1 * OLED_WIDTH + x + col] = cd;  /* Page 1 */
            }
        }
        x += 6;  /* 5px char + 1px gap */
    }

    return oled_display_flush();
}

esp_err_t oled_display_off(void)
{
    return oled_write_cmd(OLED_DISPLAY_OFF);
}

esp_err_t oled_display_on(void)
{
    return oled_write_cmd(OLED_DISPLAY_ON);
}