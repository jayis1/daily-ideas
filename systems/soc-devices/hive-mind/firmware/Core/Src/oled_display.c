/*
 * Hive Mind — SSD1306 OLED Display Driver
 * I2C 128x64 monochrome OLED for field status display
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "oled_display.h"
#include "main.h"
#include <stdio.h>
#include <string.h>

#define SSD1306_ADDR         0x3C << 1
#define SSD1306_WIDTH        128
#define SSD1306_HEIGHT       64
#define SSD1306_PAGES        (SSD1306_HEIGHT / 8)

/* Commands */
#define SSD1306_CMD_DISPLAY_OFF      0xAE
#define SSD1306_CMD_DISPLAY_ON       0xAF
#define SSD1306_CMD_SET_CONTRAST     0x81
#define SSD1306_CMD_SET_PRECHARGE    0xD9
#define SSD1306_CMD_SET_VCOM_DETECT  0xDB
#define SSD1306_CMD_SEG_REMAP        0xA1
#define SSD1306_CMD_COM_SCAN_DEC     0xC8
#define SSD1306_CMD_SET_COM_PINS     0xDA
#define SSD1306_CMD_SET_MORTIME      0xD5
#define SSD1306_CMD_SET_CHARGE_PUMP  0x8D
#define SSD1306_CMD_SET_COL_ADDR     0x21
#define SSD1306_CMD_SET_PAGE_ADDR   0x22
#define SSD1306_CMD_SET_START_LINE  0x40
#define SSD1306_CMD_MEMORY_MODE     0x20
#define SSD1306_CMD_NORMAL_DISPLAY  0xA6
#define SSD1306_CMD_ENTIRE_ON      0xA5

/* Frame buffer */
static uint8_t framebuffer[SSD1306_WIDTH * SSD1306_PAGES];
static uint8_t display_on = 0;

extern I2C_HandleTypeDef hi2c1;

/* ------------------------------------------------------------------ */
/* I2C helpers                                                         */
/* ------------------------------------------------------------------ */

static void ssd1306_send_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd};  /* Control byte = 0x00 (command) */
    HAL_I2C_Master_Transmit(&hi2c1, SSD1306_ADDR, buf, 2, 100);
}

static void ssd1306_send_cmd2(uint8_t cmd, uint8_t val)
{
    uint8_t buf[3] = {0x00, cmd, val};
    HAL_I2C_Master_Transmit(&hi2c1, SSD1306_ADDR, buf, 3, 100);
}

static void ssd1306_send_data(uint8_t *data, uint16_t len)
{
    /* Data mode: control byte = 0x40 */
    uint8_t buf[len + 1];
    buf[0] = 0x40;
    memcpy(&buf[1], data, len);
    HAL_I2C_Master_Transmit(&hi2c1, SSD1306_ADDR, buf, len + 1, 200);
}

/* ------------------------------------------------------------------ */
/* Simple 5x7 font (ASCII 32-126)                                     */
/* ------------------------------------------------------------------ */

static const uint8_t font5x7[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x5F,0x00,0x00}, /* ! */
    {0x00,0x07,0x00,0x07,0x00}, /* " */
    {0x14,0x7F,0x14,0x7F,0x14}, /* # */
    {0x24,0x2A,0x7F,0x2A,0x12}, /* $ */
    {0x23,0x13,0x08,0x64,0x62}, /* % */
    {0x36,0x49,0x55,0x22,0x50}, /* & */
    {0x00,0x05,0x03,0x00,0x00}, /* ' */
    {0x00,0x1C,0x22,0x41,0x00}, /* ( */
    {0x00,0x41,0x22,0x1C,0x00}, /* ) */
    {0x08,0x2A,0x1C,0x2A,0x08}, /* * */
    {0x08,0x08,0x3E,0x08,0x08}, /* + */
    {0x00,0x50,0x30,0x00,0x00}, /* , */
    {0x08,0x08,0x08,0x08,0x08}, /* - */
    {0x00,0x60,0x60,0x00,0x00}, /* . */
    {0x20,0x10,0x08,0x04,0x02}, /* / */
    {0x1C,0x22,0x41,0x22,0x1C}, /* 0 */
    {0x00,0x42,0x7F,0x40,0x00}, /* 1 */
    {0x42,0x61,0x51,0x49,0x46}, /* 2 */
    {0x21,0x41,0x45,0x4B,0x31}, /* 3 */
    {0x18,0x14,0x12,0x7F,0x10}, /* 4 */
    {0x27,0x45,0x45,0x45,0x39}, /* 5 */
    {0x3C,0x4A,0x49,0x49,0x30}, /* 6 */
    {0x01,0x71,0x09,0x05,0x03}, /* 7 */
    {0x36,0x49,0x49,0x49,0x36}, /* 8 */
    {0x06,0x49,0x49,0x29,0x1E}, /* 9 */
    {0x00,0x36,0x36,0x00,0x00}, /* : */
    {0x00,0x56,0x36,0x00,0x00}, /* ; */
    {0x00,0x08,0x14,0x22,0x41}, /* < */
    {0x14,0x14,0x14,0x14,0x14}, /* = */
    {0x41,0x22,0x14,0x08,0x00}, /* > */
    {0x02,0x01,0x51,0x09,0x06}, /* ? */
    {0x32,0x49,0x79,0x41,0x3E}, /* @ */
    {0x7E,0x11,0x11,0x11,0x7E}, /* A */
    {0x7F,0x49,0x49,0x49,0x36}, /* B */
    {0x3E,0x41,0x41,0x41,0x22}, /* C */
    {0x7F,0x41,0x41,0x22,0x1C}, /* D */
    {0x7F,0x49,0x49,0x49,0x41}, /* E */
    {0x7F,0x09,0x09,0x09,0x01}, /* F */
    {0x3E,0x41,0x49,0x49,0x3A}, /* G */
    {0x7F,0x08,0x08,0x08,0x7F}, /* H */
    {0x00,0x41,0x7F,0x41,0x00}, /* I */
    {0x20,0x40,0x41,0x3F,0x01}, /* J */
    {0x7F,0x08,0x14,0x22,0x41}, /* K */
    {0x7F,0x40,0x40,0x40,0x40}, /* L */
    {0x7F,0x02,0x04,0x02,0x7F}, /* M */
    {0x7F,0x04,0x08,0x10,0x7F}, /* N */
    {0x3E,0x41,0x41,0x41,0x3E}, /* O */
    {0x7F,0x09,0x09,0x09,0x06}, /* P */
    {0x3E,0x41,0x51,0x21,0x5E}, /* Q */
    {0x7F,0x09,0x19,0x29,0x46}, /* R */
    {0x26,0x49,0x49,0x49,0x32}, /* S */
    {0x01,0x01,0x7F,0x01,0x01}, /* T */
    {0x3F,0x40,0x40,0x40,0x3F}, /* U */
    {0x0F,0x30,0x40,0x30,0x0F}, /* V */
    {0x3F,0x40,0x38,0x40,0x3F}, /* W */
    {0x63,0x14,0x08,0x14,0x63}, /* X */
    {0x07,0x08,0x70,0x08,0x07}, /* Y */
    {0x61,0x51,0x49,0x45,0x43}, /* Z */
    {0x00,0x7F,0x41,0x41,0x00}, /* [ */
    {0x02,0x04,0x08,0x10,0x20}, /* backslash */
    {0x00,0x41,0x41,0x7F,0x00}, /* ] */
    {0x04,0x02,0x01,0x02,0x04}, /* ^ */
    {0x40,0x40,0x40,0x40,0x40}, /* _ */
    /* Additional characters can be added as needed */
};

/* ------------------------------------------------------------------ */
/* Drawing functions                                                    */
/* ------------------------------------------------------------------ */

static void fb_set_pixel(int x, int y, int color)
{
    if (x < 0 || x >= SSD1306_WIDTH || y < 0 || y >= SSD1306_HEIGHT) return;
    int page = y / 8;
    int bit = y % 8;
    if (color)
        framebuffer[page * SSD1306_WIDTH + x] |= (1 << bit);
    else
        framebuffer[page * SSD1306_WIDTH + x] &= ~(1 << bit);
}

static void fb_clear(void)
{
    memset(framebuffer, 0, sizeof(framebuffer));
}

static void fb_draw_char(int x, int y, char c, int scale)
{
    if (c < 32 || c > 126) c = '?';
    int idx = c - 32;
    for (int col = 0; col < 5; col++) {
        uint8_t line = font5x7[idx][col];
        for (int row = 0; row < 7; row++) {
            if (line & (1 << row)) {
                for (int dx = 0; dx < scale; dx++) {
                    for (int dy = 0; dy < scale; dy++) {
                        fb_set_pixel(x + col * scale + dx,
                                    y + row * scale + dy, 1);
                    }
                }
            }
        }
    }
}

static void fb_draw_string(int x, int y, const char *str, int scale)
{
    while (*str) {
        fb_draw_char(x, y, *str, scale);
        x += 6 * scale;
        str++;
    }
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

void oled_display_init(void)
{
    HAL_Delay(100);  /* Display power-up delay */

    /* Init sequence */
    ssd1306_send_cmd(SSD1306_CMD_DISPLAY_OFF);
    ssd1306_send_cmd2(SSD1306_CMD_SET_CONTRAST, 0x7F);
    ssd1306_send_cmd2(SSD1306_CMD_SET_PRECHARGE, 0xF1);
    ssd1306_send_cmd2(SSD1306_CMD_SET_VCOM_DETECT, 0x40);
    ssd1306_send_cmd(SSD1306_CMD_SEG_REMAP);
    ssd1306_send_cmd(SSD1306_CMD_COM_SCAN_DEC);
    ssd1306_send_cmd2(SSD1306_CMD_SET_COM_PINS, 0x12);
    ssd1306_send_cmd2(SSD1306_CMD_SET_MORTIME, 0x80);
    ssd1306_send_cmd2(SSD1306_CMD_SET_CHARGE_PUMP, 0x14);
    ssd1306_send_cmd2(SSD1306_CMD_MEMORY_MODE, 0x00);  /* Horizontal addressing */
    ssd1306_send_cmd(SSD1306_CMD_SET_START_LINE);
    ssd1306_send_cmd(SSD1306_CMD_NORMAL_DISPLAY);
    ssd1306_send_cmd(SSD1306_CMD_DISPLAY_ON);

    display_on = 1;
    fb_clear();
}

void oled_display_show(const sensor_data_t *data)
{
    char buf[22];

    fb_clear();

    /* Title */
    fb_draw_string(0, 0, "HIVE MIND", 2);

    /* Weight */
    snprintf(buf, sizeof(buf), "W: %.1f kg", data->weight_g / 1000.0f);
    fb_draw_string(0, 18, buf, 1);

    /* Temperatures */
    snprintf(buf, sizeof(buf), "F:%.1f M:%.1f C:%.1f",
             data->temp_floor, data->temp_mid, data->temp_crown);
    fb_draw_string(0, 28, buf, 1);

    /* Acoustic class */
    const char *cls_name = acoustic_class_name(data->acoustic_class);
    fb_draw_string(0, 38, cls_name, 1);

    /* Health score */
    snprintf(buf, sizeof(buf), "Health: %d/100", (int)data->health_score);
    fb_draw_string(0, 48, buf, 1);

    /* Battery */
    snprintf(buf, sizeof(buf), "B:%.1fV", data->vbat);
    fb_draw_string(90, 48, buf, 1);

    /* Flush framebuffer to display */
    ssd1306_send_cmd2(SSD1306_CMD_SET_COL_ADDR, 0);
    ssd1306_send_cmd2(SSD1306_CMD_SET_COL_ADDR + 1, SSD1306_WIDTH - 1);
    ssd1306_send_cmd2(SSD1306_CMD_SET_PAGE_ADDR, 0);
    ssd1306_send_cmd2(SSD1306_CMD_SET_PAGE_ADDR + 1, SSD1306_PAGES - 1);

    /* Send all pages */
    for (int page = 0; page < SSD1306_PAGES; page++) {
        ssd1306_send_data(&framebuffer[page * SSD1306_WIDTH], SSD1306_WIDTH);
    }
}

void oled_display_off(void)
{
    ssd1306_send_cmd(SSD1306_CMD_DISPLAY_OFF);
    display_on = 0;
}

void oled_display_on(void)
{
    ssd1306_send_cmd(SSD1306_CMD_DISPLAY_ON);
    display_on = 1;
}