/*
 * Levia Forge — SSD1306 OLED Display Driver (I2C1)
 * SPDX-License-Identifier: MIT
 */
#include "display.h"
#include "sdkconfig.h"
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include <string.h>
#include <stdio.h>

#define OLED_ADDR      0x3C
#define OLED_WIDTH     128
#define OLED_HEIGHT    64
#define OLED_PAGES     (OLED_HEIGHT / 8)

static uint8_t oled_buffer[OLED_WIDTH * OLED_PAGES];
static bool initialized = false;

static void oled_write_cmd(uint8_t cmd)
{
    uint8_t buf[2] = { 0x00, cmd };
    i2c_write_blocking(i2c1, OLED_ADDR, buf, 2, false);
}

static void oled_write_data(const uint8_t *data, size_t len)
{
    uint8_t buf[len + 1];
    buf[0] = 0x40;
    memcpy(buf + 1, data, len);
    i2c_write_blocking(i2c1, OLED_ADDR, buf, len + 1, false);
}

void display_init(void)
{
    /* Initialize I2C1 at 400 kHz */
    i2c_init(i2c1, 400000);
    gpio_set_function(PIN_I2C1_SDA, GPIO_FUNC_I2C);
    gpio_set_function(PIN_I2C1_SCL, GPIO_FUNC_I2C);
    gpio_pull_up(PIN_I2C1_SDA);
    gpio_pull_up(PIN_I2C1_SCL);

    /* SSD1306 initialization sequence */
    sleep_ms(50);
    oled_write_cmd(0xAE);  /* Display off */
    oled_write_cmd(0xD5); oled_write_cmd(0x80);  /* Set display clock divide */
    oled_write_cmd(0xA8); oled_write_cmd(0x3F);  /* Set multiplex ratio */
    oled_write_cmd(0xD3); oled_write_cmd(0x00);  /* Set display offset */
    oled_write_cmd(0x40);  /* Set start line */
    oled_write_cmd(0x8D); oled_write_cmd(0x14);  /* Enable charge pump */
    oled_write_cmd(0x20); oled_write_cmd(0x00);  /* Horizontal addressing mode */
    oled_write_cmd(0xA1);  /* Segment remap */
    oled_write_cmd(0xC8);  /* COM output scan direction */
    oled_write_cmd(0xDA); oled_write_cmd(0x12);  /* Set COM pins */
    oled_write_cmd(0x81); oled_write_cmd(0xCF);  /* Set contrast */
    oled_write_cmd(0xD9); oled_write_cmd(0xF1);  /* Set precharge period */
    oled_write_cmd(0xDB); oled_write_cmd(0x40);  /* Set VCOMH deselect */
    oled_write_cmd(0xA4);  /* Display follows RAM content */
    oled_write_cmd(0xA6);  /* Normal display (not inverted) */
    oled_write_cmd(0xAF);  /* Display on */

    memset(oled_buffer, 0, sizeof(oled_buffer));
    initialized = true;
}

/* Simple 5×8 font for text rendering */
static const uint8_t font5x8[][5] = {
    /* ASCII 32-95 (space to underscore, basic set) */
    [0]= {0x00,0x00,0x00,0x00,0x00}, /* space */
    [1]= {0x00,0x00,0x5F,0x00,0x00}, /* ! */
    /* ... abbreviated font for brevity, full font in production */
};

static void draw_pixel(int x, int y, bool on)
{
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT)
        return;
    int page = y / 8;
    int bit = y % 8;
    if (on)
        oled_buffer[page * OLED_WIDTH + x] |= (1 << bit);
    else
        oled_buffer[page * OLED_WIDTH + x] &= ~(1 << bit);
}

static void draw_text(int x, int y, const char *str)
{
    /* Simplified: write text using font5x8.
     * For production, use a full font table. */
    int cx = x;
    for (const char *p = str; *p; p++) {
        if (*p >= 32 && *p < 96) {
            int idx = *p - 32;
            for (int col = 0; col < 5; col++) {
                uint8_t bits = font5x8[idx][col];
                for (int row = 0; row < 8; row++) {
                    draw_pixel(cx + col, y + row, (bits >> row) & 1);
                }
            }
        }
        cx += 6;
    }
}

static void draw_hline(int x1, int x2, int y)
{
    for (int x = x1; x <= x2; x++)
        draw_pixel(x, y, true);
}

static void draw_vline(int x, int y1, int y2)
{
    for (int y = y1; y <= y2; y++)
        draw_pixel(x, y, true);
}

static void draw_rect(int x, int y, int w, int h)
{
    draw_hline(x, x + w - 1, y);
    draw_hline(x, x + w - 1, y + h - 1);
    draw_vline(x, y, y + h - 1);
    draw_vline(x + w - 1, y, y + h - 1);
}

static void oled_flush(void)
{
    /* Set column address range */
    oled_write_cmd(0x21);
    oled_write_cmd(0);
    oled_write_cmd(OLED_WIDTH - 1);
    /* Set page address range */
    oled_write_cmd(0x22);
    oled_write_cmd(0);
    oled_write_cmd(OLED_PAGES - 1);
    /* Write buffer */
    oled_write_data(oled_buffer, sizeof(oled_buffer));
}

static const char *pattern_names[] = {
    "POINT", "TWIN", "VORTEX", "BOTTLE", "BEND", "CONVEYOR"
};

static const char *safety_strings[] = {
    "OK", "LID OPEN", "TILT!", "LOW BAT", "HOT!", "RELEASE", "WDG", "OFF"
};

void display_show_boot(void)
{
    if (!initialized) return;
    memset(oled_buffer, 0, sizeof(oled_buffer));
    draw_rect(0, 0, 128, 64);
    draw_text(28, 12, "LEVIA FORGE");
    draw_text(20, 28, "Acoustic Levitation");
    draw_text(36, 42, "v1.0");
    oled_flush();
}

/* Forward declaration of the state struct (we use void* to avoid
 * circular includes with main.c). The actual type is levia_state_t
 * defined in main.c. We cast through a known layout. */
typedef struct {
    float target_x, target_y, target_z;
    float actual_x, actual_y, actual_z;
    int pattern;      /* phase_pattern_t */
    int vortex_charge;
    float twin_delta;
    float bend_gradient;
    float transport_progress;
    float transport_speed;
    bool active;
    bool particle_detected;
    float particle_height_mm;
    int battery_mv;
    float temp_c;
    int safety;       /* safety_state_t */
    uint32_t uptime_ms;
    bool auto_track_z;
} display_state_t;

void display_update(void *state_ptr)
{
    if (!initialized) return;
    display_state_t *s = (display_state_t *)state_ptr;
    char line[24];

    memset(oled_buffer, 0, sizeof(oled_buffer));

    /* Title bar */
    draw_text(0, 0, "LEVIA");
    if (s->active)
        draw_text(70, 0, "ACTIVE");
    else
        draw_text(70, 0, "STDBY");
    draw_hline(0, 127, 9);

    /* Position */
    snprintf(line, sizeof(line), "X:%+5.1f Y:%+5.1f", s->actual_x, s->actual_y);
    draw_text(0, 12, line);
    snprintf(line, sizeof(line), "Z:%+5.1f mm", s->actual_z);
    draw_text(0, 22, line);

    /* Pattern */
    if (s->pattern >= 0 && s->pattern < 6)
        draw_text(0, 34, pattern_names[s->pattern]);

    /* Particle status */
    if (s->particle_detected) {
        snprintf(line, sizeof(line), "OBJ:%4.1fmm", s->particle_height_mm);
        draw_text(64, 34, line);
    } else {
        draw_text(64, 34, "NO OBJ");
    }

    /* Battery + safety */
    snprintf(line, sizeof(line), "BAT:%d.%dV", s->battery_mv / 1000,
             (s->battery_mv % 1000) / 100);
    draw_text(0, 46, line);

    if (s->safety != 0) {
        if (s->safety >= 0 && s->safety < 8)
            draw_text(60, 46, safety_strings[s->safety]);
    } else {
        snprintf(line, sizeof(line), "T:%.0fC", s->temp_c);
        draw_text(60, 46, line);
    }

    /* Status bar */
    draw_hline(0, 127, 55);
    uint32_t sec = s->uptime_ms / 1000;
    snprintf(line, sizeof(line), "%dm%02ds", sec / 60, sec % 60);
    draw_text(0, 57, line);

    oled_flush();
}