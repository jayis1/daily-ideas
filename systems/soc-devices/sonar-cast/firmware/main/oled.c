/*
 * sonar-cast / firmware / oled.c
 * SSD1306 0.96" 128x64 I2C local status display.
 *
 * Shows: state, depth, bottom type, fish count, battery, GPS fix, ping rate.
 */
#include "main.h"

#define OLED_ADDR 0x3C
static bool oled_on = false;

static void oled_cmd(uint8_t c) { (void)c; }
static void oled_data(uint8_t d) { (void)d; }

void oled_init(void)
{
    /* SSD1306 init sequence (I2C):
       0xAE display off, 0xD5 0x80 clock, 0xA8 0x3F mux,
       0xD3 0x00 offset, 0x40 start line, 0x8D 0x14 charge pump,
       0x20 0x00 addr mode, 0xA1 seg remap, 0xC8 scan dir,
       0xDA 0x12 compins, 0x81 0xCF contrast, 0xD9 0xF1 precharge,
       0xDB 0x40 VCOMH, 0xA4 normal, 0xA6 non-invert, 0xAF display on */
    oled_on = true;
}

/* 5×8 font — draw a string at page y, column x (placeholder). */
static void oled_text(uint8_t x, uint8_t y, const char *s)
{
    (void)x; (void)y; (void)s;
}

/* Draw a 1-bit depth bar (0..MAX_DEPTH → 0..100 px) on the right side. */
static void oled_depth_bar(float depth_m)
{
    (void)depth_m;
}

void oled_update(const sonar_ctx_t *ctx)
{
    if (!oled_on) return;
    const sonar_result_t *r = &ctx->last;

    /* Clear */
    /* Page 0: state + battery */
    char line[22];
    const char *stn =
        ctx->state == ST_ACTIVE ? "ACT" :
        ctx->state == ST_DRIFT  ? "DRF" :
        ctx->state == ST_SLEEP  ? "SLP" : "IDL";
    snprintf(line, sizeof(line), "%s  BAT %dmV", stn, ctx->battery_mv);
    oled_text(0, 0, line);

    /* Page 1: depth + bottom */
    snprintf(line, sizeof(line), "D:%4.1fm %s",
             r->depth_m, BOTTOM_NAMES[r->bottom_type]);
    oled_text(0, 1, line);

    /* Page 2: fish */
    snprintf(line, sizeof(line), "Fish:%u  avg%.0fcm",
             r->fish_count,
             r->fish_count ? r->fish_lengths[0] : 0.0f);
    oled_text(0, 2, line);

    /* Page 3: GPS + temp */
    snprintf(line, sizeof(line), "GPS:%s T:%.1fC",
             ctx->gps_fix ? "OK" : "--", r->temp_c);
    oled_text(0, 3, line);

    /* Depth bar on right */
    oled_depth_bar(r->depth_m);
}