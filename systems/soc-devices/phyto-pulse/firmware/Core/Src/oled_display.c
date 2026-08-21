/*
 * oled_display.c — SSD1306 OLED driver
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * I2C1, 128×64 monochrome OLED.
 * Renders scrolling waveform, stats, slow-wave trend, experiment list, config.
 */

#include "oled_display.h"
#include "main.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

extern I2C_HandleTypeDef hi2c1;

#define OLED_ADDR  0x3C
#define WIDTH      128
#define HEIGHT     64

static display_mode_t g_mode = DISP_WAVE;
static char g_msg[64] = {0};
static uint32_t g_msg_until = 0;

/* Simple framebuffer (1 byte per column × 8 pages = 1024 bytes) */
static uint8_t g_fb[WIDTH * 8];

/* ---- Low-level I2C ---- */

static void oled_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd};
    HAL_I2C_Master_Transmit(&hi2c1, OLED_ADDR << 1, buf, 2, 10);
}

static void oled_data(uint8_t data)
{
    uint8_t buf[2] = {0x40, data};
    HAL_I2C_Master_Transmit(&hi2c1, OLED_ADDR << 1, buf, 2, 10);
}

static void oled_flush(void)
{
    /* Send entire framebuffer via I2C (page-by-page) */
    for (uint8_t page = 0; page < 8; page++) {
        oled_cmd(0xB0 + page);        /* Set page address */
        oled_cmd(0x00 | (0 & 0x0F));  /* Low column */
        oled_cmd(0x10 | (0 >> 4));    /* High column */
        for (int x = 0; x < WIDTH; x++) {
            oled_data(g_fb[page * WIDTH + x]);
        }
    }
}

static void fb_clear(void)
{
    memset(g_fb, 0, sizeof(g_fb));
}

/* Set/clear pixel at (x, y) */
static void fb_pixel(int x, int y, bool set)
{
    if (x < 0 || x >= WIDTH || y < 0 || y >= HEIGHT) return;
    int page = y / 8;
    int bit = y % 8;
    if (set)
        g_fb[page * WIDTH + x] |= (1 << bit);
    else
        g_fb[page * WIDTH + x] &= ~(1 << bit);
}

/* Draw a horizontal line */
static void fb_hline(int x0, int x1, int y)
{
    for (int x = x0; x <= x1; x++) fb_pixel(x, y, true);
}

/* Draw text (simple 5×7 font, uppercase only) */
static const uint8_t font5x7[][5] = {
    /* Space */ {0x00,0x00,0x00,0x00,0x00},
    /* ! */     {0x00,0x00,0x5F,0x00,0x00},
    /* : */     {0x00,0x07,0x00,0x07,0x00},
    /* - */     {0x00,0x08,0x08,0x08,0x00},
    /* . */     {0x00,0x60,0x60,0x00,0x00},
    /* 0-9 */   {0x3E,0x51,0x49,0x45,0x3E},{0x00,0x42,0x7F,0x40,0x00},
                {0x42,0x61,0x51,0x49,0x46},{0x21,0x41,0x45,0x4B,0x31},
                {0x18,0x14,0x12,0x7F,0x10},{0x27,0x45,0x45,0x45,0x39},
                {0x3C,0x4A,0x49,0x49,0x30},{0x01,0x71,0x09,0x05,0x03},
                {0x36,0x49,0x49,0x49,0x36},{0x06,0x49,0x49,0x29,0x1E},
    /* A-Z (subset) */
    /* A */ {0x7E,0x11,0x11,0x11,0x7E},{0x7F,0x49,0x49,0x49,0x36},
    /* C */ {0x3E,0x41,0x41,0x41,0x22},{0x7F,0x41,0x41,0x22,0x1C},
    /* E */ {0x7F,0x09,0x09,0x09,0x01},{0x7F,0x09,0x09,0x09,0x01},
    /* G */ {0x3E,0x41,0x49,0x49,0x7A},{0x7F,0x08,0x08,0x08,0x7F},
    /* I */ {0x00,0x41,0x7F,0x41,0x00},{0x20,0x40,0x41,0x3F,0x01},
    /* K */ {0x7F,0x08,0x14,0x22,0x41},{0x7F,0x40,0x40,0x40,0x40},
    /* M */ {0x7F,0x02,0x0C,0x02,0x7F},{0x7F,0x04,0x08,0x10,0x7F},
    /* O */ {0x3E,0x41,0x41,0x41,0x3E},{0x7F,0x09,0x09,0x09,0x06},
    /* Q */ {0x3E,0x41,0x51,0x21,0x5E},{0x7F,0x09,0x19,0x29,0x46},
    /* S */ {0x46,0x49,0x49,0x49,0x31},{0x01,0x01,0x7F,0x01,0x01},
    /* U */ {0x3F,0x40,0x40,0x40,0x3F},{0x1F,0x20,0x40,0x20,0x1F},
    /* W */ {0x7F,0x20,0x18,0x20,0x7F},{0x63,0x14,0x08,0x14,0x63},
    /* Y */ {0x07,0x08,0x70,0x08,0x07},{0x61,0x51,0x49,0x45,0x43},
};

static void fb_text(int x, int y, const char *text)
{
    int cx = x;
    for (int i = 0; text[i] && cx < WIDTH - 5; i++) {
        char c = text[i];
        const uint8_t *glyph = font5x7[0]; /* default: space */
        if (c >= '0' && c <= '9') glyph = font5x7[5 + (c - '0')];
        else if (c >= 'A' && c <= 'Z') glyph = font5x7[15 + (c - 'A')];
        else if (c == ' ') glyph = font5x7[0];
        else if (c == '!') glyph = font5x7[1];
        else if (c == ':') glyph = font5x7[2];
        else if (c == '-') glyph = font5x7[3];
        else if (c == '.') glyph = font5x7[4];

        for (int col = 0; col < 5; col++) {
            uint8_t bits = glyph[col];
            for (int row = 0; row < 7; row++) {
                if (bits & (1 << row)) {
                    fb_pixel(cx + col, y + row, true);
                }
            }
        }
        cx += 6;
    }
}

/* ---- Public API ---- */

void oled_init(void)
{
    /* SSD1306 init sequence */
    HAL_Delay(50);
    oled_cmd(0xAE);  /* Display off */
    oled_cmd(0xD5); oled_cmd(0x80);  /* Clock divide */
    oled_cmd(0xA8); oled_cmd(0x3F);  /* Multiplex */
    oled_cmd(0xD3); oled_cmd(0x00);  /* Offset */
    oled_cmd(0x40);  /* Start line */
    oled_cmd(0x8D); oled_cmd(0x14);  /* Charge pump */
    oled_cmd(0x20); oled_cmd(0x00);  /* Addressing mode */
    oled_cmd(0xA1);  /* Segment remap */
    oled_cmd(0xC8);  /* COM scan dir */
    oled_cmd(0xDA); oled_cmd(0x12);  /* COM pins */
    oled_cmd(0xD9); oled_cmd(0xF1);  /* Pre-charge */
    oled_cmd(0xDB); oled_cmd(0x40);  /* VCOM */
    oled_cmd(0xA4);  /* Display on from RAM */
    oled_cmd(0xA6);  /* Normal display */
    oled_cmd(0xAF);  /* Display on */
    HAL_Delay(100);
    fb_clear();
    oled_flush();
}

void oled_set_mode(display_mode_t mode) { g_mode = mode; }
display_mode_t oled_get_mode(void) { return g_mode; }

void oled_next_mode(void)
{
    g_mode = (display_mode_t)((g_mode + 1) % 5);
}

static void draw_waveform(float current_value, float threshold, float baseline,
                          bool recording)
{
    /* Title */
    fb_text(0, 0, recording ? "REC" : "IDLE");
    fb_text(40, 0, "WAVE");

    /* Draw threshold lines */
    int th_y = 32 - (int)(threshold * 10);
    if (th_y > 8 && th_y < HEIGHT) fb_hline(0, WIDTH-1, th_y);
    int bl_y = 32 - (int)(baseline * 10);
    if (bl_y > 8 && bl_y < HEIGHT) fb_hline(0, WIDTH-1, bl_y);

    /* Current value indicator (right edge) */
    int val_y = 32 - (int)(current_value * 10);
    if (val_y < 8) val_y = 8;
    if (val_y > HEIGHT - 1) val_y = HEIGHT - 1;
    for (int x = WIDTH - 8; x < WIDTH; x++) {
        fb_pixel(x, val_y, true);
    }
}

static void draw_stats(uint16_t event_count, uint16_t ap_count,
                       uint16_t vp_count, uint16_t art_count,
                       float battery_v, float ina_gain)
{
    char buf[24];
    fb_text(0, 0, "STATS");
    fb_text(0, 12, "EVT:");
    snprintf(buf, sizeof(buf), "%d", event_count);
    fb_text(30, 12, buf);
    fb_text(0, 24, "AP:");
    snprintf(buf, sizeof(buf), "%d", ap_count);
    fb_text(30, 24, buf);
    fb_text(0, 36, "VP:");
    snprintf(buf, sizeof(buf), "%d", vp_count);
    fb_text(30, 36, buf);
    fb_text(0, 48, "BAT:");
    snprintf(buf, sizeof(buf), "%.1fV", battery_v);
    fb_text(30, 48, buf);
    snprintf(buf, sizeof(buf), "G%.0f", ina_gain);
    fb_text(80, 48, buf);
}

static void draw_swp(float swp_mean)
{
    char buf[24];
    fb_text(0, 0, "SWP");
    fb_text(0, 16, "MEAN:");
    snprintf(buf, sizeof(buf), "%.2fmV", swp_mean);
    fb_text(40, 16, buf);
}

static void draw_experiment(int8_t current_exp)
{
    fb_text(0, 0, "EXP");
    if (current_exp >= 0) {
        char buf[20];
        snprintf(buf, sizeof(buf), "RUN:%d", current_exp);
        fb_text(0, 16, buf);
    } else {
        fb_text(0, 16, "SELECT:");
        fb_text(0, 28, "MODE+");
        fb_text(0, 40, "STIM=GO");
    }
}

static void draw_config(float threshold, float baseline, float ina_gain,
                         uint32_t sample_count, float bat_v)
{
    char buf[24];
    fb_text(0, 0, "CFG");
    snprintf(buf, sizeof(buf), "G:%.0f", ina_gain);
    fb_text(0, 12, buf);
    snprintf(buf, sizeof(buf), "TH:%.1f", threshold);
    fb_text(0, 24, buf);
    snprintf(buf, sizeof(buf), "N:%lu", (unsigned long)sample_count);
    fb_text(0, 36, buf);
    snprintf(buf, sizeof(buf), "B:%.1fV", bat_v);
    fb_text(0, 48, buf);
}

void oled_update(float current_value, float threshold, float baseline,
                  uint32_t sample_count, uint16_t event_count,
                  uint16_t ap_count, uint16_t vp_count, uint16_t art_count,
                  float battery_v, float ina_gain,
                  bool recording, int8_t current_experiment)
{
    fb_clear();

    /* Check for temporary message */
    if (g_msg[0] && HAL_GetTick() < g_msg_until) {
        fb_text(0, 28, g_msg);
    } else {
        switch (g_mode) {
            case DISP_WAVE:
                draw_waveform(current_value, threshold, baseline, recording);
                break;
            case DISP_STATS:
                draw_stats(event_count, ap_count, vp_count, art_count,
                          battery_v, ina_gain);
                break;
            case DISP_SWP:
                draw_swp(baseline);
                break;
            case DISP_EXP:
                draw_experiment(current_experiment);
                break;
            case DISP_CONFIG:
                draw_config(threshold, baseline, ina_gain, sample_count, battery_v);
                break;
        }
    }

    oled_flush();
}

void oled_show_message(const char *msg, uint32_t duration_ms)
{
    strncpy(g_msg, msg, sizeof(g_msg) - 1);
    g_msg[sizeof(g_msg) - 1] = 0;
    g_msg_until = HAL_GetTick() + duration_ms;
}

void oled_clear(void)
{
    fb_clear();
    oled_flush();
}

void oled_off(void) { oled_cmd(0xAE); }
void oled_on(void)  { oled_cmd(0xAF); }