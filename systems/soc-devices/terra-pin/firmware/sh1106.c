/**
 * terra_pin/sh1106.c — SH1106 1.3" OLED display driver (I2C, 128×64)
 *
 * Simple frame-buffer driver for the SH1106 OLED controller.
 * I2C address 0x3C, shared bus via TCA9548A channel 2 (passthrough).
 *
 * The display shows:
 *   - Large SHI number (0–100) with color-coded label
 *   - Respiration bar (mg C m⁻² h⁻¹)
 *   - ORP, EC, VWC, Temp readouts
 *   - Battery icon and mode indicator
 */

#include "sh1106.h"
#include "esp_log.h"
#include "driver/i2c.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "SH1106";

/* SH1106 commands */
#define SH1106_SET_CONTRAST       0x81
#define SH1106_DISPLAY_ON         0xAF
#define SH1106_DISPLAY_OFF        0xAE
#define SH1106_SET_PAGE_ADDR      0xB0
#define SH1106_SET_COL_LOW        0x00
#define SH1106_SET_COL_HIGH       0x10
#define SH1106_SET_SEG_REMAP      0xA1
#define SH1106_SET_COM_SCAN_INV   0xC8

static uint8_t g_fb[SH1106_HEIGHT / 8][SH1106_WIDTH];

/* ── 5x7 font (compact subset) ────────────────────────────────────── */

static const uint8_t font5x7[][5] = {
    /* 0-9 */
    {0x3E,0x51,0x49,0x45,0x3E}, {0x00,0x42,0x7F,0x40,0x00},
    {0x42,0x61,0x51,0x49,0x46}, {0x21,0x41,0x45,0x4B,0x31},
    {0x18,0x14,0x12,0x7F,0x10}, {0x27,0x45,0x45,0x45,0x39},
    {0x3C,0x4A,0x49,0x49,0x30}, {0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36}, {0x06,0x49,0x49,0x29,0x1E},
};

static void sh1106_write_cmd(uint8_t cmd)
{
    i2c_cmd_handle_t h = i2c_cmd_link_create();
    i2c_master_start(h);
    i2c_master_write_byte(h, (SH1106_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(h, 0x00, true);  /* Co=0, D/C=0 → command */
    i2c_master_write_byte(h, cmd, true);
    i2c_master_stop(h);
    i2c_master_cmd_begin(I2C_NUM_0, h, pdMS_TO_TICKS(50));
    i2c_cmd_link_delete(h);
}

static void sh1106_write_data_page(uint8_t page, const uint8_t *data, int len)
{
    i2c_cmd_handle_t h = i2c_cmd_link_create();
    i2c_master_start(h);
    i2c_master_write_byte(h, (SH1106_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(h, 0x00, true);  /* command */
    i2c_master_write_byte(h, SH1106_SET_PAGE_ADDR | page, true);
    i2c_master_write_byte(h, SH1106_SET_COL_LOW | 2, true);  /* col offset */
    i2c_master_write_byte(h, SH1106_SET_COL_HIGH, true);
    i2c_master_stop(h);
    i2c_master_cmd_begin(I2C_NUM_0, h, pdMS_TO_TICKS(50));
    i2c_cmd_link_delete(h);

    /* Data burst */
    h = i2c_cmd_link_create();
    i2c_master_start(h);
    i2c_master_write_byte(h, (SH1106_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(h, 0x40, true);  /* Co=0, D/C=1 → data */
    i2c_master_write(h, data, len, true);
    i2c_master_stop(h);
    i2c_master_cmd_begin(I2C_NUM_0, h, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(h);
}

esp_err_t sh1106_init(void)
{
    ESP_LOGI(TAG, "Initializing SH1106 OLED");

    sh1106_write_cmd(SH1106_DISPLAY_OFF);
    vTaskDelay(pdMS_TO_TICKS(10));
    sh1106_write_cmd(SH1106_SET_SEG_REMAP);
    sh1106_write_cmd(SH1106_SET_COM_SCAN_INV);
    sh1106_write_cmd(SH1106_SET_CONTRAST);
    sh1106_write_cmd(0xCF);
    sh1106_write_cmd(SH1106_DISPLAY_ON);

    memset(g_fb, 0, sizeof(g_fb));
    ESP_LOGI(TAG, "SH1106 initialized");
    return ESP_OK;
}

static void fb_draw_char(int x, int y, char c, bool large)
{
    if (c < '0' || c > '9') return;
    int idx = c - '0';
    int scale = large ? 2 : 1;
    for (int col = 0; col < 5; col++) {
        uint8_t bits = font5x7[idx][col];
        for (int row = 0; row < 7; row++) {
            if (bits & (1 << row)) {
                for (int dy = 0; dy < scale; dy++)
                    for (int dx = 0; dx < scale; dx++) {
                        int px = x + col * scale + dx;
                        int py = y + row * scale + dy;
                        if (px < SH1106_WIDTH && py < SH1106_HEIGHT)
                            g_fb[py / 8][px] |= (1 << (py % 8));
                    }
            }
        }
    }
}

static void fb_draw_text(int x, int y, const char *str, bool large)
{
    int spacing = large ? 12 : 6;
    for (int i = 0; str[i]; i++)
        fb_draw_char(x + i * spacing, y, str[i], large);
}

static void fb_draw_hline(int x, int y, int len)
{
    for (int i = 0; i < len; i++)
        if (x + i < SH1106_WIDTH)
            g_fb[y / 8][x + i] |= (1 << (y % 8));
}

static void fb_clear(void)
{
    memset(g_fb, 0, sizeof(g_fb));
}

static void fb_flush(void)
{
    for (int p = 0; p < SH1106_HEIGHT / 8; p++)
        sh1106_write_data_page(p, g_fb[p], SH1106_WIDTH);
}

void sh1106_update(const terra_reading_t *r, uint8_t battery_pct, terra_mode_t mode)
{
    xSemaphoreTake(g_i2c_mutex, portMAX_DELAY);

    /* Select OLED via mux passthrough channel */
    i2c_cmd_handle_t h = i2c_cmd_link_create();
    i2c_master_start(h);
    i2c_master_write_byte(h, (TCA9548A_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(h, TCA9548A_CH_OLED, true);
    i2c_master_stop(h);
    i2c_master_cmd_begin(I2C_NUM_0, h, pdMS_TO_TICKS(50));
    i2c_cmd_link_delete(h);

    fb_clear();

    /* SHI big number (2x scale) at top-left */
    char shi_str[4];
    snprintf(shi_str, sizeof(shi_str), "%3d", r->shi);
    fb_draw_text(0, 0, shi_str, true);  /* large 2x digits */

    /* SHI label + bar */
    fb_draw_hline(0, 20, r->shi);  /* simple bar — 1 px per SHI point */

    /* Parameter readouts (small text, line by line) */
    char line[20];
    snprintf(line, sizeof(line), "FLUX %4.1f mgC", r->flux_mgC);
    fb_draw_text(0, 24, line, false);

    snprintf(line, sizeof(line), "ORP %+5d mV", r->orp_mv);
    fb_draw_text(0, 32, line, false);

    snprintf(line, sizeof(line), "EC  %5u uS", r->ec_us);
    fb_draw_text(0, 40, line, false);

    snprintf(line, sizeof(line), "VWC %4.1f%%", r->moisture_vwc);
    fb_draw_text(0, 48, line, false);

    snprintf(line, sizeof(line), "T  %4.1fC BAT%3d", r->temp_c, battery_pct);
    fb_draw_text(0, 56, line, false);

    /* Mode indicator (right side) */
    const char *mode_str = (mode == MODE_POINT) ? "P" :
                           (mode == MODE_CONTINUOUS) ? "C" : "L";
    fb_draw_text(120, 0, mode_str, false);

    fb_flush();

    /* Deselect mux */
    h = i2c_cmd_link_create();
    i2c_master_start(h);
    i2c_master_write_byte(h, (TCA9548A_I2C_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(h, 0x00, true);
    i2c_master_stop(h);
    i2c_master_cmd_begin(I2C_NUM_0, h, pdMS_TO_TICKS(50));
    i2c_cmd_link_delete(h);

    xSemaphoreGive(g_i2c_mutex);
}