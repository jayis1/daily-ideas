/*
 * display.c — SSD1306 128×64 OLED via I2C
 *
 * Renders: patch name, octave, breath bar, battery %, BLE/USB status.
 */
#include "display.h"
#include "driver/i2c.h"
#include "esp_log.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "disp";
static bool inited = false;

#define I2C_SDA 8
#define I2C_SCL 9
#define OLED_ADDR 0x3C

/* Minimal SSD1306 command interface (no external lib needed for demo) */
static void oled_cmd(uint8_t cmd);
static void oled_data(const uint8_t *buf, int len);

/* Framebuffer: 128×64 = 1024 pixels = 128 bytes × 8 pages */
static uint8_t fb[128 * 8];

void display_init(void)
{
    i2c_config_t cfg = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_SDA, .scl_io_num = I2C_SCL,
        .sda_pullup_en = true, .scl_pullup_en = true,
        .master.clk_speed = 400000,
    };
    i2c_param_config(I2C_NUM_0, &cfg);
    i2c_driver_install(I2C_NUM_0, I2C_MODE_MASTER, 0, 0, 0);

    /* SSD1306 init sequence */
    oled_cmd(0xAE);  /* display off */
    oled_cmd(0xD5); oled_cmd(0x80);  /* clock divide */
    oled_cmd(0xA8); oled_cmd(0x3F);  /* multiplex 64 */
    oled_cmd(0xD3); oled_cmd(0x00);  /* display offset */
    oled_cmd(0x40);  /* start line 0 */
    oled_cmd(0x8D); oled_cmd(0x14);  /* charge pump on */
    oled_cmd(0x20); oled_cmd(0x00);  /* addressing mode horizontal */
    oled_cmd(0xA1);  /* segment remap */
    oled_cmd(0xC8);  /* COM scan dir */
    oled_cmd(0xDA); oled_cmd(0x12);  /* COM pins */
    oled_cmd(0xD9); oled_cmd(0xF1);  /* precharge */
    oled_cmd(0xDB); oled_cmd(0x40);  /* VCOMH */
    oled_cmd(0x81); oled_cmd(0xCF);  /* contrast */
    oled_cmd(0xA4);  /* display RAM */
    oled_cmd(0xA6);  /* normal display */
    oled_cmd(0xAF);  /* display on */

    memset(fb, 0, sizeof(fb));
    inited = true;
    ESP_LOGI(TAG, "OLED SSD1306 initialised at 0x%02X", OLED_ADDR);
}

static void oled_cmd(uint8_t cmd)
{
    uint8_t buf[2] = { 0x00, cmd };
    i2c_master_write_to_device(I2C_NUM_0, OLED_ADDR, buf, 2, pdMS_TO_TICKS(100));
}

static void oled_data(const uint8_t *buf, int len)
{
    /* Control byte 0x40 = data stream */
    uint8_t tmp[len + 1];
    tmp[0] = 0x40;
    memcpy(&tmp[1], buf, len);
    i2c_master_write_to_device(I2C_NUM_0, OLED_ADDR, tmp, len + 1, pdMS_TO_TICKS(100));
}

static void flush_fb(void)
{
    for (int page = 0; page < 8; page++) {
        oled_cmd(0xB0 + page);
        oled_cmd(0x00);  /* col low */
        oled_cmd(0x10);  /* col high */
        oled_data(&fb[page * 128], 128);
    }
}

/* Tiny 5×7 font (subset of ASCII) */
#include "font5x7.h"

static void draw_char(int x, int y, char c)
{
    if (c < 32 || c > 127) c = '?';
    const uint8_t *glyph = &font5x7[(c - 32) * 5];
    for (int col = 0; col < 5; col++) {
        uint8_t bits = glyph[col];
        for (int row = 0; row < 7; row++) {
            if (bits & (1 << row)) {
                int px = x + col;
                int py = y + row;
                if (px < 128 && py < 64) {
                    fb[(py / 8) * 128 + px] |= (1 << (py % 8));
                }
            }
        }
    }
}

static void draw_str(int x, int y, const char *s)
{
    while (*s) {
        draw_char(x, y, *s);
        x += 6;
        s++;
    }
}

/* Draw a horizontal bar (x, y, width, height, value 0..1) */
static void draw_bar(int x, int y, int w, int h, float v01)
{
    if (v01 < 0) v01 = 0; if (v01 > 1) v01 = 1;
    int fill = (int)(v01 * w);
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < w; c++) {
            int px = x + c, py = y + r;
            if (px < 128 && py < 64) {
                int byte_idx = (py / 8) * 128 + px;
                if (c < fill)
                    fb[byte_idx] |= (1 << (py % 8));
                else
                    fb[byte_idx] &= ~(1 << (py % 8));
            }
        }
    }
}

void display_update(const aero_state_t *st)
{
    if (!inited) return;
    memset(fb, 0, sizeof(fb));

    /* Patch name (top) */
    char line[20];
    snprintf(line, sizeof(line), "P%d:%s",
             st->patch_idx, st->patch.name);
    draw_str(0, 0, line);

    /* Status icons (top right) */
    if (st->ble_connected) draw_str(96, 0, "BT");
    if (st->usb_connected) draw_str(112, 0, "USB");

    /* Breath bar (middle) */
    draw_str(0, 16, "BREATH");
    draw_bar(48, 16, 80, 6, (float)st->breath_vel / 127.0f);

    /* Note display */
    if (st->current_note >= 0) {
        const char *notes[] = {"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
        snprintf(line, sizeof(line), "NOTE:%s%d",
                 notes[st->current_note % 12], st->current_note / 12 - 1);
        draw_str(0, 28, line);
    } else {
        draw_str(0, 28, "NOTE:--");
    }

    /* Battery + charge status */
    snprintf(line, sizeof(line), "BAT:%d%%", st->battery_pct);
    draw_str(0, 40, line);
    if (st->charging) draw_str(60, 40, "CHG");

    /* Bend indicator */
    int bend_disp = st->bend_cents / 10;
    snprintf(line, sizeof(line), "BEND:%+d", bend_disp);
    draw_str(0, 52, line);

    flush_fb();
}