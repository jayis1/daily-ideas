/*
 * display.c — SSD1306 OLED display driver (128×64, I2C)
 * Opti Rot — Pocket Digital Polarimeter
 *
 * Drives the SSD1306 OLED via I2C1. Provides text rendering (8×16 font),
 * simple line/bar drawing, and polarimetry-specific display layouts.
 */
#include "stm32g4xx_hal.h"
#include <stdio.h>
#include <string.h>
#include "sdkconfig.h"
#include "display.h"

extern I2C_HandleTypeDef hi2c1;

/* SSD1306 commands */
#define SSD1306_SET_CONTRAST    0x81
#define SSD1306_DISPLAY_ON      0xAF
#define SSD1306_DISPLAY_OFF     0xAE
#define SSD1306_SET_COL_ADDR    0x21
#define SSD1306_SET_PAGE_ADDR    0x22
#define SSD1306_NORMAL_DISPLAY   0xA6
#define SSD1306_ADDR_MODE horizontal 0x00

/* Display buffer (128×64 = 1024 bytes, 8 pages of 128) */
static uint8_t display_buffer[1024];

/* Simple 5×8 font (ASCII 32-127). Each char = 5 bytes + 1 spacing byte. */
/* Using a minimal font for digits, uppercase, common symbols. */
/* (In production, use a full font table. Here we include a compact subset.) */

#include <string.h>

static const uint8_t font5x8[][5] = {
    /* space */ {0x00,0x00,0x00,0x00,0x00},
    /* !     */ {0x00,0x00,0x5F,0x00,0x00},
    /* "     */ {0x00,0x07,0x00,0x07,0x00},
    /* #     */ {0x14,0x7F,0x14,0x7F,0x14},
    /* $     */ {0x24,0x2A,0x7F,0x2A,0x12},
    /* %     */ {0x23,0x13,0x08,0x64,0x62},
    /* &     */ {0x36,0x49,0x55,0x22,0x50},
    /* '     */ {0x00,0x05,0x03,0x00,0x00},
    /* (     */ {0x00,0x1C,0x22,0x41,0x00},
    /* )     */ {0x00,0x41,0x22,0x1C,0x00},
    /* *     */ {0x08,0x2A,0x1C,0x2A,0x08},
    /* +     */ {0x08,0x08,0x3E,0x08,0x08},
    /* ,     */ {0x00,0x50,0x30,0x00,0x00},
    /* -     */ {0x08,0x08,0x08,0x08,0x08},
    /* .     */ {0x00,0x60,0x60,0x00,0x00},
    /* /     */ {0x20,0x10,0x08,0x04,0x02},
    /* 0-9 */ {0x3E,0x51,0x49,0x45,0x3E},
    {0x00,0x42,0x7F,0x40,0x00},
    {0x42,0x61,0x51,0x49,0x46},
    {0x21,0x41,0x45,0x4B,0x31},
    {0x18,0x14,0x12,0x7F,0x10},
    {0x27,0x45,0x45,0x45,0x39},
    {0x3C,0x4A,0x49,0x49,0x30},
    {0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36},
    {0x06,0x49,0x49,0x29,0x1E},
    /* :     */ {0x00,0x36,0x36,0x00,0x00},
    /* ;     */ {0x00,0x56,0x36,0x00,0x00},
    /* <     */ {0x00,0x08,0x14,0x22,0x41},
    /* =     */ {0x14,0x14,0x14,0x14,0x14},
    /* >     */ {0x41,0x22,0x14,0x08,0x00},
    /* ?     */ {0x02,0x01,0x51,0x09,0x06},
    /* @     */ {0x32,0x49,0x79,0x41,0x3E},
    /* A-Z */ {0x7E,0x11,0x11,0x11,0x7E},
    {0x7F,0x49,0x49,0x49,0x36},
    {0x7F,0x01,0x01,0x01,0x01},
    {0x7F,0x01,0x01,0x01,0x7E},
    {0x7F,0x09,0x09,0x09,0x01},
    {0x7F,0x09,0x09,0x09,0x06},
    {0x3E,0x41,0x41,0x41,0x22},
    {0x7F,0x08,0x08,0x08,0x7F},
    {0x00,0x41,0x7F,0x41,0x00},
    {0x02,0x01,0x01,0x7F,0x40},
    {0x7F,0x08,0x14,0x22,0x41},
    {0x7F,0x40,0x40,0x40,0x40},
    {0x7F,0x02,0x04,0x02,0x7F},
    {0x7F,0x02,0x0C,0x02,0x7F},
    {0x3E,0x41,0x41,0x41,0x3E},
    {0x7F,0x09,0x09,0x09,0x06},
    {0x3E,0x41,0x49,0x49,0x7A},
    {0x7F,0x09,0x19,0x29,0x46},
    {0x26,0x49,0x49,0x49,0x32},
    {0x01,0x01,0x7F,0x01,0x01},
    {0x3F,0x40,0x40,0x40,0x3F},
    {0x1F,0x20,0x20,0x20,0x1F},
    {0x07,0x18,0x60,0x18,0x07},
    {0x63,0x14,0x08,0x14,0x63},
    {0x03,0x04,0x78,0x04,0x03},
    {0x61,0x51,0x49,0x45,0x43},
    {0x00,0x00,0x00,0x00,0x00},  /* [ */
    {0x00,0x00,0x00,0x00,0x00},  /* \ */
    {0x00,0x00,0x00,0x00,0x00},  /* ] */
    {0x00,0x00,0x00,0x00,0x00},  /* ^ */
    {0x08,0x08,0x08,0x08,0x08},  /* _ */
    /* a-z (lowercase, compact) */
    {0x20,0x54,0x54,0x54,0x78},
    {0x3F,0x44,0x44,0x44,0x38},
    {0x38,0x44,0x44,0x44,0x20},
    {0x38,0x44,0x44,0x44,0x3F},
    {0x38,0x54,0x54,0x54,0x08},
    {0x08,0x7E,0x09,0x01,0x02},
    {0x08,0x14,0x54,0x22,0x38},
    {0x3F,0x08,0x04,0x04,0x02},
    {0x00,0x41,0x7F,0x41,0x00},
    {0x04,0x02,0x3F,0x02,0x04},
    {0x08,0x14,0x14,0x14,0x1C},
    {0x04,0x04,0x3F,0x04,0x04},
    {0x00,0x38,0x44,0x44,0x20},
    {0x04,0x34,0x2C,0x24,0x04},
    {0x00,0x00,0x7F,0x44,0x38},
    {0x7F,0x10,0x08,0x04,0x00},
    {0x41,0x7F,0x41,0x00,0x00},
    {0x7C,0x04,0x04,0x78,0x00},
    {0x7C,0x04,0x04,0x78,0x00},  /* v same as u rotated, approx */
    {0x38,0x44,0x44,0x44,0x38},
    {0x7C,0x18,0x18,0x18,0x00},  /* w approx */
    {0x44,0x28,0x10,0x28,0x44},
    {0x0C,0x50,0x50,0x50,0x3C},
    {0x44,0x64,0x54,0x4C,0x44},
    {0x00,0x00,0x00,0x00,0x00},  /* z approx */
};

static void ssd1306_command(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd};
    HAL_I2C_Master_Transmit(&hi2c1, OLED_I2C_ADDR << 1, buf, 2, HAL_MAX_DELAY);
}

static void ssd1306_data(uint8_t *data, uint16_t len)
{
    uint8_t buf[129];
    buf[0] = 0x40;
    memcpy(&buf[1], data, len);
    HAL_I2C_Master_Transmit(&hi2c1, OLED_I2C_ADDR << 1, buf, len + 1, HAL_MAX_DELAY);
}

static void display_flush(void)
{
    for (uint8_t page = 0; page < 8; page++) {
        ssd1306_command(0x21);  /* set column addr */
        ssd1306_command(0x00);
        ssd1306_command(0x7F);
        ssd1306_command(0x22);  /* set page addr */
        ssd1306_command(page);
        ssd1306_command(page);
        ssd1306_data(&display_buffer[page * 128], 128);
    }
}

void display_clear_buffer(void)
{
    memset(display_buffer, 0, sizeof(display_buffer));
}

static void draw_char(int x, int y, char c)
{
    if (c < 32 || c > 127) c = '?';
    int idx = c - 32;
    if (idx >= (int)(sizeof(font5x8) / sizeof(font5x8[0])))
        idx = 0;
    for (int i = 0; i < 5; i++) {
        uint8_t col = font5x8[idx][i];
        for (int j = 0; j < 8; j++) {
            if (col & (1 << j)) {
                int px = x + i;
                int py = y + j;
                if (px >= 0 && px < 128 && py >= 0 && py < 64) {
                    display_buffer[px + (py / 8) * 128] |= (1 << (py % 8));
                }
            }
        }
    }
}

static void draw_text(int x, int y, const char *text)
{
    int cx = x;
    for (const char *p = text; *p; p++) {
        draw_char(cx, y, *p);
        cx += 6;  /* 5px char + 1px spacing */
    }
}

void display_init(void)
{
    /* SSD1306 initialization sequence */
    ssd1306_command(0xAE);  /* display off */
    ssd1306_command(0xD5); ssd1306_command(0x80);  /* clock divide */
    ssd1306_command(0xA8); ssd1306_command(0x3F);  /* multiplex */
    ssd1306_command(0xD3); ssd1306_command(0x00);  /* display offset */
    ssd1306_command(0x40);  /* start line = 0 */
    ssd1306_command(0x8D); ssd1306_command(0x14);  /* charge pump on */
    ssd1306_command(0x20); ssd1306_command(0x00);  /* addr mode horizontal */
    ssd1306_command(0xA1);  /* segment remap */
    ssd1306_command(0xC8);  /* COM scan direction */
    ssd1306_command(0xDA); ssd1306_command(0x12);  /* COM pins */
    ssd1306_command(0x81); ssd1306_command(0xCF);  /* contrast */
    ssd1306_command(0xD9); ssd1306_command(0xF1);  /* pre-charge */
    ssd1306_command(0xDB); ssd1306_command(0x40);  /* VCOM deselect */
    ssd1306_command(0xA4);  /* display resume */
    ssd1306_command(0xA6);  /* normal display (not inverted) */
    ssd1306_command(0xAF);  /* display on */

    display_clear_buffer();
    display_flush();
}

void display_splash(const char *title, const char *subtitle)
{
    display_clear_buffer();
    draw_text(40, 16, title);
    draw_text(34, 36, subtitle);
    display_flush();
}

static const char *mode_names[] = {
    "MEASURE", "IDENTIFY", "MONITOR", "LIBRARY", "CALIBRATE", "CONFIG"
};

void display_main_menu(uint8_t mode)
{
    char buf[22];
    display_clear_buffer();
    draw_text(0, 0,  "OPTI ROT");
    draw_text(0, 12, "--------");
    snprintf(buf, sizeof(buf), "> %s", mode_names[mode]);
    draw_text(0, 28, buf);
    draw_text(0, 52, "MEAS  MODE  CAL");
    display_flush();
}

void display_message(const char *line1, const char *line2)
{
    display_clear_buffer();
    if (line1) draw_text(0, 24, line1);
    if (line2) draw_text(0, 40, line2);
    display_flush();
}

void display_measurement(double rotation, double concentration,
                          const char *compound, double confidence)
{
    char buf[22];
    display_clear_buffer();
    draw_text(0, 0, "MEASUREMENT");
    draw_text(0, 12, "-----------");
    snprintf(buf, sizeof(buf), "Rot: %+6.3f deg", rotation);
    draw_text(0, 24, buf);
    if (compound) {
        snprintf(buf, sizeof(buf), "%-20s", compound);
        draw_text(0, 36, buf);
        snprintf(buf, sizeof(buf), "Conf: %.0f%%", confidence);
        draw_text(0, 48, buf);
    } else {
        snprintf(buf, sizeof(buf), "Conc: %.2f g/100mL", concentration);
        draw_text(0, 36, buf);
    }
    display_flush();
}

void display_drude(double K, double lambda0, double alpha405,
                    double alpha520, double alpha589)
{
    char buf[22];
    display_clear_buffer();
    draw_text(0, 0, "DRUDE ORD FIT");
    draw_text(0, 12, "-------------");
    snprintf(buf, sizeof(buf), "405: %+.1f deg", alpha405);
    draw_text(0, 24, buf);
    snprintf(buf, sizeof(buf), "520: %+.1f deg", alpha520);
    draw_text(0, 34, buf);
    snprintf(buf, sizeof(buf), "589: %+.1f deg", alpha589);
    draw_text(0, 44, buf);
    snprintf(buf, sizeof(buf), "K=%.1E l0=%.0f", K, lambda0);
    draw_text(0, 56, buf);
    display_flush();
}

void display_temperature(double temp_c)
{
    /* Small overlay in top-right corner */
    char buf[10];
    snprintf(buf, sizeof(buf), "%.1fC", temp_c);
    draw_text(96, 0, buf);
    /* Note: caller should flush */
}

void display_library(int index, int total, const char *name, double alpha_d)
{
    char buf[22];
    display_clear_buffer();
    draw_text(0, 0, "LIBRARY");
    draw_text(0, 12, "-------");
    snprintf(buf, sizeof(buf), "%d/%d", index + 1, total);
    draw_text(0, 26, buf);
    draw_text(0, 38, name);
    snprintf(buf, sizeof(buf), "[a]D=%+.1f", alpha_d);
    draw_text(0, 52, buf);
    display_flush();
}

void display_off(void)
{
    ssd1306_command(SSD1306_DISPLAY_OFF);
}

void display_on(void)
{
    ssd1306_command(SSD1306_DISPLAY_ON);
}