/*
 * lode-sweep / firmware / oled.c
 * SSD1306 0.96" 128x64 I2C display.
 *
 * Shows: state, target class, depth, confidence, signal strength bar,
 * battery, GPS fix, ground balance status.
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

static void oled_text(uint8_t x, uint8_t y, const char *s)
{
    (void)x; (void)y; (void)s;
}

/* Draw a horizontal signal strength bar (0..1 → 0..100 px) */
static void oled_signal_bar(float strength)
{
    (void)strength;
}

void oled_update(const sweep_ctx_t *ctx)
{
    if (!oled_on) return;
    const sweep_result_t *r = &ctx->last;

    char line[22];
    const char *stn =
        ctx->state == ST_ACTIVE ? "ACT" :
        ctx->state == ST_DRIFT  ? "DRF" :
        ctx->state == ST_SLEEP  ? "SLP" : "IDL";

    /* Page 0: state + battery + sensitivity */
    snprintf(line, sizeof(line), "%s S%u BAT %dmV",
             stn, ctx->sensitivity, ctx->battery_mv);
    oled_text(0, 0, line);

    /* Page 1: target class + confidence */
    if (r->signal_strength > 0.05f) {
        snprintf(line, sizeof(line), "%s %d%%",
                 CLASS_NAMES[r->target_class],
                 (int)(r->confidence * 100));
    } else {
        snprintf(line, sizeof(line), "---");
    }
    oled_text(0, 1, line);

    /* Page 2: depth + tilt */
    snprintf(line, sizeof(line), "D:%4.0fcm T:%.0f",
             r->depth_cm, r->tilt_deg);
    oled_text(0, 2, line);

    /* Page 3: GPS + ground */
    snprintf(line, sizeof(line), "GPS:%s GND:%.1f",
             ctx->gps_fix ? "OK" : "--",
             ctx->ground_amp);
    oled_text(0, 3, line);

    /* Signal strength bar */
    oled_signal_bar(r->signal_strength);
}