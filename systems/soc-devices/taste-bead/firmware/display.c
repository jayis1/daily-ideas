/* display.c — SSD1306 OLED display driver
 *
 * Minimal SSD1306 driver for the Taste Bead's 128×64 OLED.
 * Uses I2C at 400 kHz. Supports text rendering with a small font
 * and simple graphics (progress bars, confidence indicators).
 */

#include "display.h"
#include "sdkconfig.h"
#include "esp_log.h"
#include "driver/i2c.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "display";

/* Frame buffer: 128×64 = 1024 bytes, organized as 8 pages of 128 bytes */
static uint8_t g_framebuf[DISPLAY_WIDTH * DISPLAY_PAGES];
static bool g_initialized = false;

/* ---- 5×8 font (ASCII 0x20-0x7F) ---- */
static const uint8_t font5x8[][5] = {
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
    {0x14,0x08,0x3E,0x08,0x14}, /* * */
    {0x08,0x08,0x3E,0x08,0x08}, /* + */
    {0x00,0x50,0x30,0x00,0x00}, /* , */
    {0x08,0x08,0x08,0x08,0x08}, /* - */
    {0x00,0x60,0x60,0x00,0x00}, /* . */
    {0x20,0x10,0x08,0x04,0x02}, /* / */
    {0x3E,0x51,0x49,0x45,0x3E}, /* 0 */
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
    {0x08,0x14,0x22,0x41,0x00}, /* < */
    {0x14,0x14,0x14,0x14,0x14}, /* = */
    {0x00,0x41,0x22,0x14,0x08}, /* > */
    {0x02,0x01,0x51,0x09,0x06}, /* ? */
    {0x3E,0x41,0x49,0x49,0x4A}, /* @ */
    /* A-Z */
    {0x7E,0x11,0x11,0x11,0x7E}, {0x7F,0x49,0x49,0x49,0x36},
    {0x3E,0x41,0x41,0x41,0x22}, {0x7F,0x41,0x41,0x22,0x1C},
    {0x7F,0x49,0x49,0x49,0x41}, {0x7F,0x09,0x09,0x09,0x01},
    {0x3E,0x41,0x41,0x51,0x32}, {0x7F,0x08,0x08,0x08,0x7F},
    {0x00,0x41,0x7F,0x41,0x00}, {0x20,0x40,0x40,0x40,0x3F},
    {0x7F,0x08,0x14,0x22,0x41}, {0x7F,0x40,0x40,0x40,0x40},
    {0x7F,0x02,0x04,0x02,0x7F}, {0x7F,0x04,0x08,0x10,0x7F},
    {0x3E,0x41,0x41,0x41,0x3E}, {0x7F,0x09,0x09,0x09,0x06},
    {0x3E,0x41,0x51,0x21,0x5E}, {0x7F,0x09,0x19,0x29,0x46},
    {0x46,0x49,0x49,0x49,0x31}, {0x01,0x01,0x7F,0x01,0x01},
    {0x3F,0x40,0x40,0x40,0x3F}, {0x1F,0x20,0x40,0x20,0x1F},
    {0x3F,0x40,0x38,0x40,0x3F}, {0x63,0x14,0x08,0x14,0x63},
    /* a-z (partial) */
    {0x7C,0x12,0x11,0x12,0x7C}, {0x7F,0x49,0x49,0x49,0x36},
    {0x3E,0x41,0x41,0x41,0x22}, {0x7F,0x41,0x41,0x22,0x1C},
    {0x7F,0x49,0x49,0x49,0x41}, {0x7F,0x09,0x09,0x09,0x01},
    {0x3E,0x41,0x41,0x51,0x32}, {0x7F,0x08,0x08,0x08,0x7F},
    {0x00,0x41,0x7F,0x41,0x00}, {0x20,0x40,0x40,0x40,0x3F},
    {0x7F,0x08,0x14,0x22,0x41}, {0x7F,0x40,0x40,0x40,0x40},
    {0x7F,0x02,0x04,0x02,0x7F}, {0x7F,0x04,0x08,0x10,0x7F},
    {0x3E,0x41,0x41,0x41,0x3E}, {0x7F,0x09,0x09,0x09,0x06},
    {0x3E,0x41,0x51,0x21,0x5E}, {0x7F,0x09,0x19,0x29,0x46},
    {0x46,0x49,0x49,0x49,0x31}, {0x01,0x01,0x7F,0x01,0x01},
    {0x3F,0x40,0x40,0x40,0x3F}, {0x1F,0x20,0x40,0x20,0x1F},
    {0x3F,0x40,0x38,0x40,0x3F}, {0x63,0x14,0x08,0x14,0x63},
    {0x7C,0x12,0x11,0x12,0x7C}, {0x7C,0x12,0x11,0x12,0x7C},
};

/* I2C write helper */
static esp_err_t i2c_write_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00, cmd};
    return i2c_master_write_to_device(I2C_NUM_0, SSD1306_I2C_ADDR,
                                        (const uint8_t *)buf, 2, pdMS_TO_TICKS(100));
}

static esp_err_t i2c_write_data(const uint8_t *data, int len)
{
    uint8_t buf[129];
    buf[0] = 0x40; /* data byte */
    memcpy(buf + 1, data, len);
    return i2c_master_write_to_device(I2C_NUM_0, SSD1306_I2C_ADDR,
                                        buf, len + 1, pdMS_TO_TICKS(100));
}

/* Draw a character at (x, y) in the frame buffer */
static void draw_char(int x, int y, char c)
{
    if (x < 0 || x + 5 > DISPLAY_WIDTH || y < 0 || y + 8 > DISPLAY_HEIGHT) return;

    int idx = c - 0x20;
    if (idx < 0 || idx >= (int)(sizeof(font5x8) / sizeof(font5x8[0]))) idx = 0;

    int page = y / 8;
    for (int col = 0; col < 5; col++) {
        g_framebuf[page * DISPLAY_WIDTH + x + col] = font5x8[idx][col];
    }
    /* 1-pixel gap after character */
    g_framebuf[page * DISPLAY_WIDTH + x + 5] = 0x00;
}

/* Draw a string starting at (x, y) */
static void draw_string(int x, int y, const char *str)
{
    int cx = x;
    for (int i = 0; str[i] && cx + 6 <= DISPLAY_WIDTH; i++) {
        draw_char(cx, y, str[i]);
        cx += 6;
    }
}

/* Draw a horizontal line */
static void draw_hline(int x, int y, int width, uint8_t pattern)
{
    int page = y / 8;
    for (int i = 0; i < width && x + i < DISPLAY_WIDTH; i++) {
        g_framebuf[page * DISPLAY_WIDTH + x + i] = pattern;
    }
}

/* Flush frame buffer to OLED */
static void display_flush(void)
{
    if (!g_initialized) return;

    for (int page = 0; page < DISPLAY_PAGES; page++) {
        i2c_write_cmd(0xB0 + page);     /* page address */
        i2c_write_cmd(0x00);             /* lower column address = 0 */
        i2c_write_cmd(0x10);             /* upper column address = 0 */
        i2c_write_data(&g_framebuf[page * DISPLAY_WIDTH], DISPLAY_WIDTH);
    }
}

esp_err_t display_init(void)
{
    /* Configure I2C bus (shared with BME280) */
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = PIN_I2C_SDA,
        .scl_io_num = PIN_I2C_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = 400000,
    };
    i2c_param_config(I2C_NUM_0, &conf);
    i2c_driver_install(I2C_NUM_0, I2C_MODE_MASTER, 0, 0, 0);

    /* SSD1306 initialization sequence */
    vTaskDelay(pdMS_TO_TICKS(50)); /* wait for display power-up */

    i2c_write_cmd(0xAE); /* display off */
    i2c_write_cmd(0xD5); i2c_write_cmd(0x80); /* clock divide ratio */
    i2c_write_cmd(0xA8); i2c_write_cmd(0x3F); /* multiplex ratio = 64 */
    i2c_write_cmd(0xD3); i2c_write_cmd(0x00); /* display offset = 0 */
    i2c_write_cmd(0x40); /* start line = 0 */
    i2c_write_cmd(0x8D); i2c_write_cmd(0x14); /* charge pump enable */
    i2c_write_cmd(0x20); i2c_write_cmd(0x00); /* page addressing mode */
    i2c_write_cmd(0xA1); /* segment remap */
    i2c_write_cmd(0xC8); /* COM output scan direction (remapped) */
    i2c_write_cmd(0xDA); i2c_write_cmd(0x12); /* COM pins = alternate */
    i2c_write_cmd(0x81); i2c_write_cmd(0xCF); /* contrast */
    i2c_write_cmd(0xD9); i2c_write_cmd(0xF1); /* pre-charge period */
    i2c_write_cmd(0xDB); i2c_write_cmd(0x40); /* VCOMH deselect level */
    i2c_write_cmd(0xA4); /* display follows RAM content */
    i2c_write_cmd(0xA6); /* normal display (not inverted) */
    i2c_write_cmd(0xAF); /* display ON */

    memset(g_framebuf, 0, sizeof(g_framebuf));
    display_flush();
    g_initialized = true;

    ESP_LOGI(TAG, "SSD1306 OLED initialized");
    return ESP_OK;
}

esp_err_t display_show_splash(const char *title, const char *subtitle)
{
    memset(g_framebuf, 0, sizeof(g_framebuf));
    draw_string(0, 0, title);
    draw_string(0, 12, subtitle);
    draw_hline(0, 22, DISPLAY_WIDTH, 0x01);
    display_flush();
    return ESP_OK;
}

esp_err_t display_show_message(const char *line1, const char *line2)
{
    memset(g_framebuf, 0, sizeof(g_framebuf));
    draw_string(0, 0, line1 ? line1 : "");
    draw_string(0, 12, line2 ? line2 : "");
    display_flush();
    return ESP_OK;
}

esp_err_t display_show_result(const char *label, const char *confidence_str,
                                float confidence_pct)
{
    memset(g_framebuf, 0, sizeof(g_framebuf));

    /* Title bar */
    draw_string(0, 0, "IDENTIFIED:");
    draw_hline(0, 10, DISPLAY_WIDTH, 0x01);

    /* Label (line 1, 16px high) */
    draw_string(0, 14, label ? label : "Unknown");

    /* Confidence text */
    draw_string(0, 28, confidence_str ? confidence_str : "");

    /* Confidence bar (bottom of screen) */
    draw_string(0, 40, "Confidence:");
    int bar_x = 0;
    int bar_y = 52;
    int bar_width = DISPLAY_WIDTH;
    int bar_fill = (int)(bar_width * confidence_pct / 100.0f);

    /* Bar outline */
    draw_hline(bar_x, bar_y, bar_width, 0x01);
    draw_hline(bar_x, bar_y + 7, bar_width, 0x80);

    /* Bar fill */
    if (bar_fill > 0) {
        for (int i = 0; i < bar_fill; i++) {
            g_framebuf[(bar_y / 8) * DISPLAY_WIDTH + bar_x + i] = 0xFF;
        }
    }

    display_flush();
    return ESP_OK;
}

esp_err_t display_show_library(int index, int total, const char *label,
                                int measurement_count)
{
    memset(g_framebuf, 0, sizeof(g_framebuf));
    char header[32];
    snprintf(header, sizeof(header), "LIB %d/%d", index + 1, total);
    draw_string(0, 0, header);
    draw_hline(0, 10, DISPLAY_WIDTH, 0x01);
    draw_string(0, 14, label ? label : "(empty)");

    char count_str[32];
    snprintf(count_str, sizeof(count_str), "%d measurements", measurement_count);
    draw_string(0, 28, count_str);
    display_flush();
    return ESP_OK;
}

esp_err_t display_show_progress(const char *label, int percent)
{
    memset(g_framebuf, 0, sizeof(g_framebuf));
    draw_string(0, 0, label ? label : "Working...");
    draw_hline(0, 10, DISPLAY_WIDTH, 0x01);

    int bar_y = 20;
    int bar_width = DISPLAY_WIDTH;
    int bar_fill = bar_width * percent / 100;

    for (int i = 0; i < bar_width; i++) {
        g_framebuf[(bar_y / 8) * DISPLAY_WIDTH + i] = 0x01;
    }
    if (bar_fill > 0) {
        for (int i = 0; i < bar_fill; i++) {
            g_framebuf[(bar_y / 8) * DISPLAY_WIDTH + i] = 0xFF;
        }
    }

    char pct_str[16];
    snprintf(pct_str, sizeof(pct_str), "%d%%", percent);
    draw_string(0, 32, pct_str);

    display_flush();
    return ESP_OK;
}

esp_err_t display_show_monitor(const char *last_label, float last_conf,
                                 int sweep_count)
{
    memset(g_framebuf, 0, sizeof(g_framebuf));
    draw_string(0, 0, "MONITORING");
    draw_hline(0, 10, DISPLAY_WIDTH, 0x01);

    char count_str[32];
    snprintf(count_str, sizeof(count_str), "Sweeps: %d", sweep_count);
    draw_string(0, 14, count_str);

    if (last_label && strlen(last_label) > 0) {
        draw_string(0, 28, last_label);
        char conf_str[32];
        snprintf(conf_str, sizeof(conf_str), "%.0f%% conf", last_conf);
        draw_string(0, 40, conf_str);
    } else {
        draw_string(0, 28, "Measuring...");
    }

    display_flush();
    return ESP_OK;
}

esp_err_t display_clear(void)
{
    memset(g_framebuf, 0, sizeof(g_framebuf));
    display_flush();
    return ESP_OK;
}

esp_err_t display_off(void)
{
    i2c_write_cmd(0xAE); /* display off */
    return ESP_OK;
}