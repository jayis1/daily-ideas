/*
 * Melody Sprite — RP2040 FM Synthesizer
 * display.c — SSD1306 OLED display rendering
 *
 * Renders waveform, parameters, sequencer, and menu screens
 * on a 128×64 I2C OLED display (SSD1306).
 */

#include "display.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

/* SSD1306 I2C commands */
#define SSD1306_CMD      0x00
#define SSD1306_DATA     0x40
#define SSD1306_SETCONTRAST    0x81
#define SSD1306_DISPLAYALLON   0xA5
#define SSD1306_DISPLAYNORMAL  0xA6
#define SSD1306_DISPLAYOFF     0xAE
#define SSD1306_DISPLAYON      0xAF
#define SSD1306_SETDISPLAYOFFSET 0xD3
#define SSD1306_SETCOMSCANDEC  0xC8
#define SSD1306_SETSEGMENTMAP  0xA1
#define SSD1306_SETMULTIPLEX   0xA8
#define SSD1306_SETLOWCOLUMN   0x00
#define SSD1306_SETHIGHCOLUMN  0x10
#define SSD1306_SETPAGEADDR    0xB0
#define SSD1306_SETCHARGEPUMP  0x8D
#define SSD1306_SETSTARTLINE   0x40
#define SSD1306_MEMORYMODE     0x20

/* I2C address */
#define OLED_I2C_ADDR  0x3C

/* 5×7 ASCII font (printable chars 0x20–0x7E) */
static const uint8_t font5x7[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    /* Simplified font — full font table would go here */
    /* In production, include full 95-character ASCII font */
};

/* Stub I2C write (would use pico hardware_i2c) */
static int oled_write_cmd(uint8_t cmd) { (void)cmd; return 0; }
static int oled_write_data(const uint8_t *data, int len) { (void)data; (void)len; return 0; }

void display_init(display_t *disp)
{
    memset(disp, 0, sizeof(display_t));
    disp->mode = DISPLAY_MODE_BOOT;
    disp->dirty = true;

    /* SSD1306 initialization sequence */
    oled_write_cmd(SSD1306_DISPLAYOFF);
    oled_write_cmd(SSD1306_SETMULTIPLEX);  oled_write_cmd(63);       /* 1/64 duty */
    oled_write_cmd(SSD1306_SETDISPLAYOFFSET); oled_write_cmd(0x00);   /* No offset */
    oled_write_cmd(SSD1306_SETSTARTLINE);                             /* Start line 0 */
    oled_write_cmd(SSD1306_SETCHARGEPUMP); oled_write_cmd(0x14);      /* Enable charge pump */
    oled_write_cmd(SSD1306_MEMORYMODE); oled_write_cmd(0x01);         /* Vertical addressing */
    oled_write_cmd(SSD1306_SETSEGMENTMAP);                            /* Column 127 = seg0 */
    oled_write_cmd(SSD1306_SETCOMSCANDEC);                            /* COM scan direction */
    oled_write_cmd(SSD1306_SETCONTRAST); oled_write_cmd(0xCF);        /* Contrast */
    oled_write_cmd(SSD1306_DISPLAYNORMAL);
    oled_write_cmd(SSD1306_DISPLAYON);
}

void display_set_mode(display_t *disp, display_mode_t mode)
{
    disp->mode = mode;
    disp->dirty = true;
}

void display_set_pixel(display_t *disp, int x, int y, bool on)
{
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;

    int page = y / 8;
    int bit = y % 8;
    int idx = page * OLED_WIDTH + x;

    if (on) {
        disp->framebuffer[idx] |= (1 << bit);
    } else {
        disp->framebuffer[idx] &= ~(1 << bit);
    }
}

void display_hline(display_t *disp, int x, int y, int w, bool on)
{
    for (int i = 0; i < w; i++) {
        display_set_pixel(disp, x + i, y, on);
    }
}

void display_vline(display_t *disp, int x, int y, int h, bool on)
{
    for (int i = 0; i < h; i++) {
        display_set_pixel(disp, x, y + i, on);
    }
}

void display_rect(display_t *disp, int x, int y, int w, int h, bool on)
{
    display_hline(disp, x, y, w, on);
    display_hline(disp, x, y + h - 1, w, on);
    display_vline(disp, x, y, h, on);
    display_vline(disp, x + w - 1, y, h, on);
}

void display_rect_filled(display_t *disp, int x, int y, int w, int h, bool on)
{
    for (int dy = 0; dy < h; dy++) {
        for (int dx = 0; dx < w; dx++) {
            display_set_pixel(disp, x + dx, y + dy, on);
        }
    }
}

void display_char(display_t *disp, int x, int y, char c, bool on)
{
    if (c < 0x20 || c > 0x7E) c = '?';
    int idx = c - 0x20;
    for (int col = 0; col < 5; col++) {
        uint8_t bits = font5x7[idx][col];
        for (int row = 0; row < 7; row++) {
            if (bits & (1 << row)) {
                display_set_pixel(disp, x + col, y + row, on);
            }
        }
    }
}

void display_string(display_t *disp, int x, int y, const char *str, bool on)
{
    while (*str) {
        display_char(disp, x, y, *str, on);
        x += 6; /* 5 pixel char + 1 pixel spacing */
        str++;
    }
}

void display_number(display_t *disp, int x, int y, int num, bool on)
{
    char buf[12];
    snprintf(buf, sizeof(buf), "%d", num);
    display_string(disp, x, y, buf, on);
}

/* --- Render modes --- */

static void render_waveform(display_t *disp)
{
    /* Clear framebuffer */
    memset(disp->framebuffer, 0, sizeof(disp->framebuffer));

    /* Title */
    display_string(disp, 0, 0, "MELODY SPRITE", true);

    /* Draw waveform from audio buffer */
    if (disp->waveform_buf && disp->waveform_len > 0) {
        int wave_y = 20; /* Start line */
        int wave_h = 36; /* Waveform height */
        int mid = wave_y + wave_h / 2;

        /* Center line */
        display_hline(disp, 0, mid, OLED_WIDTH, true);

        /* Plot waveform samples */
        for (int x = 0; x < OLED_WIDTH && x < disp->waveform_len; x++) {
            int idx = (x * disp->waveform_len) / OLED_WIDTH;
            int16_t sample = disp->waveform_buf[idx * 2]; /* Left channel */
            int y = mid - (sample * wave_h / 2) / 32768;

            if (y < wave_y) y = wave_y;
            if (y >= wave_y + wave_h) y = wave_y + wave_h - 1;

            display_set_pixel(disp, x, y, true);
            if (y > mid) {
                for (int fy = mid; fy <= y; fy++)
                    display_set_pixel(disp, x, fy, true);
            } else {
                for (int fy = y; fy <= mid; fy++)
                    display_set_pixel(disp, x, fy, true);
            }
        }
    }

    /* Bottom status bar */
    display_string(disp, 0, 56, "V:8 BPM:120", true);
    display_string(disp, 96, 56, "BLE", true);
}

static void render_params(display_t *disp)
{
    memset(disp->framebuffer, 0, sizeof(disp->framebuffer));

    /* Voice number */
    display_string(disp, 0, 0, "VOICE ", true);
    display_number(disp, 42, 0, disp->active_voice + 1, true);

    /* 4 parameter bars (one per pot) */
    for (int i = 0; i < 4; i++) {
        param_display_t *p = &disp->params[i];
        int y = 14 + i * 13;

        /* Parameter name */
        display_string(disp, 0, y, p->name, true);

        /* Parameter value as text */
        char val_str[12];
        if (p->unit[0] != '\0') {
            snprintf(val_str, sizeof(val_str), "%.1f%s", p->value, p->unit);
        } else {
            snprintf(val_str, sizeof(val_str), "%.0f", p->value);
        }
        display_string(disp, 70, y, val_str, true);

        /* Progress bar */
        int bar_x = 42;
        int bar_w = 24;
        float pct = (p->value - p->min_val) / (p->max_val - p->min_val + 0.001f);
        int fill_w = (int)(pct * bar_w);
        display_rect(disp, bar_x, y + 1, bar_w, 5, true);
        display_rect_filled(disp, bar_x + 1, y + 2, fill_w, 3, true);
    }
}

static void render_sequencer(display_t *disp)
{
    memset(disp->framebuffer, 0, sizeof(disp->framebuffer));

    seq_display_t *s = &disp->seq;

    /* Header: mode + tempo */
    if (s->playing) {
        display_string(disp, 0, 0, "SEQ PLAY", true);
    } else if (s->recording) {
        display_string(disp, 0, 0, "SEQ REC", true);
    } else {
        display_string(disp, 0, 0, "SEQ EDIT", true);
    }
    display_number(disp, 80, 0, s->tempo, true);
    display_string(disp, 100, 0, "BPM", true);

    /* Step grid: 16 steps × 4 banks = 64 steps shown as 4 rows of 16 */
    for (int bank = 0; bank < 4; bank++) {
        for (int step = 0; step < 16; step++) {
            int global_step = bank * 16 + step;
            int x = step * 8;
            int y = 12 + bank * 14;

            /* Determine if step has a note */
            bool has_note = (s->pattern[global_step / 8] >> (global_step % 8)) & 1;

            /* Current step highlight */
            if (global_step == s->current_step) {
                display_rect_filled(disp, x, y, 7, 12, has_note);
            } else if (has_note) {
                display_rect_filled(disp, x + 1, y + 2, 5, 8, true);
            } else {
                display_rect(disp, x, y, 7, 12, true);
            }
        }
    }

    /* Bottom: current note info */
    display_string(disp, 0, 56, "STEP:", true);
    display_number(disp, 36, 56, s->current_step + 1, true);
}

static void render_boot(display_t *disp)
{
    memset(disp->framebuffer, 0, sizeof(disp->framebuffer));

    /* Boot splash — "Melody Sprite" with a music note */
    display_string(disp, 10, 10, "MELODY", true);
    display_string(disp, 10, 24, "SPRITE", true);

    /* Simple music note icon */
    display_vline(disp, 80, 8, 16, true);
    display_rect_filled(disp, 76, 22, 8, 6, true);
    display_hline(disp, 80, 8, 12, true);

    display_string(disp, 20, 42, "v1.0", true);
    display_string(disp, 60, 56, "RP2040", true);
}

static void render_ble_pairing(display_t *disp)
{
    memset(disp->framebuffer, 0, sizeof(disp->framebuffer));

    display_string(disp, 0, 0, "BLE PAIRING", true);
    display_string(disp, 0, 14, "Searching...", true);

    if (disp->ble_paired) {
        display_string(disp, 0, 28, "PAIRED:", true);
        display_string(disp, 0, 42, disp->ble_name, true);
    } else {
        /* Animated dots */
        static int dots = 0;
        dots = (dots + 1) % 4;
        for (int i = 0; i < dots; i++) {
            display_rect_filled(disp, 50 + i * 8, 28, 6, 6, true);
        }
    }
}

void display_render(display_t *disp)
{
    switch (disp->mode) {
    case DISPLAY_MODE_WAVEFORM:  render_waveform(disp); break;
    case DISPLAY_MODE_PARAMS:     render_params(disp); break;
    case DISPLAY_MODE_SEQUENCER:  render_sequencer(disp); break;
    case DISPLAY_MODE_MENU:       /* TODO: menu rendering */ break;
    case DISPLAY_MODE_BOOT:       render_boot(disp); break;
    case DISPLAY_MODE_BLE_PAIRING: render_ble_pairing(disp); break;
    }
    disp->dirty = true;
}

void display_flush(display_t *disp)
{
    if (!disp->dirty) return;

    /* Send framebuffer to OLED via I2C */
    for (int page = 0; page < OLED_PAGES; page++) {
        oled_write_cmd(SSD1306_SETPAGEADDR | page);
        oled_write_cmd(SSD1306_SETLOWCOLUMN | 0);
        oled_write_cmd(SSD1306_SETHIGHCOLUMN | 0);
        oled_write_data(&disp->framebuffer[page * OLED_WIDTH], OLED_WIDTH);
    }

    disp->dirty = false;
}

void display_set_waveform(display_t *disp, int16_t *buf, int len)
{
    disp->waveform_buf = buf;
    disp->waveform_len = len;
}

void display_set_param(display_t *disp, int index, const char *name,
                        float value, float min, float max, const char *unit)
{
    if (index < 0 || index >= 4) return;
    param_display_t *p = &disp->params[index];
    strncpy(p->name, name, sizeof(p->name) - 1);
    p->value = value;
    p->min_val = min;
    p->max_val = max;
    strncpy(p->unit, unit, sizeof(p->unit) - 1);
}

void display_set_seq_data(display_t *disp, const seq_display_t *seq_data)
{
    memcpy(&disp->seq, seq_data, sizeof(seq_display_t));
}