/*
 * Spectra Charm — ESP32-C3 SSD1306 OLED Display Manager
 *
 * oled_ui.c — UI rendering and display management
 */

#include "oled_ui.h"
#include <string.h>
#include <stdio.h>
#include "esp_log.h"
#include "driver/i2c.h"

static const char *TAG = "OLED_UI";

/* SSD1306 commands */
#define SSD1306_CMD      0x00
#define SSD1306_DATA     0x40
#define SSD1306_DISPLAY_OFF      0xAE
#define SSD1306_DISPLAY_ON       0xAF
#define SSD1306_SET_DISP_CLK    0xD5
#define SSD1306_SET_MUX_RATIO   0xA8
#define SSD1306_SET_DISP_OFFSET 0xD3
#define SSD1306_SET_START_LINE  0x40
#define SSD1306_SET_CHARGE_PUMP 0x8D
#define SSD1306_SET_MEM_MODE    0x20
#define SSD1306_SEG_REMAP       0xA1
#define SSD1306_COM_SCAN_DEC    0xC8
#define SSD1306_SET_COM_PIN     0xDA
#define SSD1306_SET_CONTRAST    0x81
#define SSD1306_SET_PRECHARGE   0xD9
#define SSD1306_SET_VCOM_DESEL  0xDB
#define SSD1306_ENTIRE_ON       0xA5
#define SSD1306_NORMAL_DISP     0xA6
#define SSD1306_SET_COL_ADDR    0x21
#define SSD1306_SET_PAGE_ADDR   0x22

#define OLED_WIDTH  128
#define OLED_HEIGHT 64
#define OLED_PAGES  (OLED_HEIGHT / 8)

/* Framebuffer — 128 × 64 / 8 = 1024 bytes */
static uint8_t framebuffer[OLED_WIDTH * OLED_PAGES];
static i2c_port_t i2c_num;
static uint8_t i2c_addr;
static int8_t rst_gpio;

/* Font: 5x7 ASCII (printable 0x20-0x7E) */
#include "font5x7.h"

static void oled_write_cmd(uint8_t cmd)
{
    uint8_t buf[2] = { SSD1306_CMD, cmd };
    i2c_cmd_handle_t handle = i2c_cmd_link_create();
    i2c_master_start(handle);
    i2c_master_write_byte(handle, (i2c_addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write(handle, buf, 2, true);
    i2c_master_stop(handle);
    i2c_master_cmd_begin(i2c_num, handle, 100 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(handle);
}

static void oled_write_data(const uint8_t *data, uint16_t len)
{
    i2c_cmd_handle_t handle = i2c_cmd_link_create();
    i2c_master_start(handle);
    i2c_master_write_byte(handle, (i2c_addr << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(handle, SSD1306_DATA, true);
    i2c_master_write(handle, (uint8_t *)data, len, true);
    i2c_master_stop(handle);
    i2c_master_cmd_begin(i2c_num, handle, 100 / portTICK_PERIOD_MS);
    i2c_cmd_link_delete(handle);
}

void OLED_Init(i2c_port_t port, uint8_t addr, int8_t reset_gpio)
{
    i2c_num = port;
    i2c_addr = addr;
    rst_gpio = reset_gpio;

    /* Hardware reset */
    if (reset_gpio >= 0) {
        gpio_set_direction(reset_gpio, GPIO_MODE_OUTPUT);
        gpio_set_level(reset_gpio, 0);
        vTaskDelay(pdMS_TO_TICKS(10));
        gpio_set_level(reset_gpio, 1);
        vTaskDelay(pdMS_TO_TICKS(10));
    }

    /* SSD1306 initialization sequence */
    oled_write_cmd(SSD1306_DISPLAY_OFF);
    oled_write_cmd(SSD1306_SET_MUX_RATIO); oled_write_cmd(63);
    oled_write_cmd(SSD1306_SET_DISP_OFFSET); oled_write_cmd(0);
    oled_write_cmd(SSD1306_SET_START_LINE);
    oled_write_cmd(0x20); oled_write_cmd(0x00); /* Horizontal addressing */
    oled_write_cmd(SSD1306_SEG_REMAP);
    oled_write_cmd(SSD1306_COM_SCAN_DEC);
    oled_write_cmd(SSD1306_SET_COM_PIN); oled_write_cmd(0x12);
    oled_write_cmd(SSD1306_SET_CONTRAST); oled_write_cmd(0xCF);
    oled_write_cmd(SSD1306_SET_PRECHARGE); oled_write_cmd(0xF1);
    oled_write_cmd(SSD1306_SET_VCOM_DESEL); oled_write_cmd(0x40);
    oled_write_cmd(SSD1306_SET_CHARGE_PUMP); oled_write_cmd(0x14);
    oled_write_cmd(SSD1306_SET_DISP_CLK); oled_write_cmd(0x80);
    oled_write_cmd(SSD1306_NORMAL_DISP);
    oled_write_cmd(SSD1306_DISPLAY_ON);

    memset(framebuffer, 0, sizeof(framebuffer));
    ESP_LOGI(TAG, "OLED initialized");
}

void OLED_Clear(void)
{
    memset(framebuffer, 0, sizeof(framebuffer));
}

void OLED_Refresh(void)
{
    oled_write_cmd(SSD1306_SET_COL_ADDR); oled_write_cmd(0); oled_write_cmd(127);
    oled_write_cmd(SSD1306_SET_PAGE_ADDR); oled_write_cmd(0); oled_write_cmd(7);
    oled_write_data(framebuffer, sizeof(framebuffer));
}

void OLED_DrawPixel(int x, int y, int on)
{
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;
    int page = y / 8;
    int bit = y % 8;
    if (on) {
        framebuffer[x + page * OLED_WIDTH] |= (1 << bit);
    } else {
        framebuffer[x + page * OLED_WIDTH] &= ~(1 << bit);
    }
}

void OLED_DrawChar(int x, int y, char c, int scale)
{
    if (c < 0x20 || c > 0x7E) c = '?';
    int glyph_idx = c - 0x20;

    for (int col = 0; col < 5; col++) {
        uint8_t line = font5x7[glyph_idx * 5 + col];
        for (int row = 0; row < 7; row++) {
            if (line & (1 << row)) {
                for (int sx = 0; sx < scale; sx++) {
                    for (int sy = 0; sy < scale; sy++) {
                        OLED_DrawPixel(x + col * scale + sx, y + row * scale + sy, 1);
                    }
                }
            }
        }
    }
}

void OLED_DrawString(int x, int y, const char *str, int scale)
{
    while (*str) {
        OLED_DrawChar(x, y, *str, scale);
        x += 6 * scale;
        str++;
    }
}

void OLED_DrawLine(int x0, int y0, int x1, int y1)
{
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;

    for (;;) {
        OLED_DrawPixel(x0, y0, 1);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

void OLED_ShowSplash(void)
{
    OLED_Clear();
    OLED_DrawString(10, 8, "Spectra", 2);
    OLED_DrawString(22, 28, "Charm", 2);
    OLED_DrawString(24, 48, "v1.0", 1);
    OLED_Refresh();
}

void OLED_ShowScreen(OLEDScreen_t screen)
{
    OLED_Clear();

    switch (screen) {
    case SCREEN_HOME:
        OLED_DrawString(2, 0, "Spectra Charm", 1);
        OLED_DrawLine(0, 10, 127, 10);
        OLED_DrawString(2, 16, "> Scan", 1);
        OLED_DrawString(2, 26, "  Library", 1);
        OLED_DrawString(2, 36, "  Settings", 1);
        OLED_DrawString(80, 56, "87%", 1);
        break;

    case SCREEN_SCANNING:
        OLED_DrawString(20, 16, "Scanning...", 2);
        OLED_DrawString(20, 40, "Please wait", 1);
        break;

    case SCREEN_RESULT: {
        OLED_DrawString(2, 0, "Result:", 1);
        /* Mini spectrum plot */
        OLED_DrawLine(0, 30, 127, 30); /* Baseline */
        /* Simple bar chart of 8 channels across display */
        for (int i = 0; i < 8; i++) {
            int h = 8 + (i * 3) % 16; /* Placeholder heights */
            int x = 8 + i * 15;
            for (int y = 30 - h; y < 30; y++) {
                OLED_DrawPixel(x, y, 1);
                OLED_DrawPixel(x + 1, y, 1);
                OLED_DrawPixel(x + 2, y, 1);
            }
        }
        OLED_DrawString(2, 40, "Match:", 1);
        OLED_DrawString(2, 52, "KMnO4 92%", 1);
        break;
    }

    case SCREEN_LOW_BATTERY:
        OLED_DrawString(8, 20, "LOW BATTERY", 2);
        OLED_DrawString(20, 48, "Charge!", 1);
        break;

    default:
        OLED_DrawString(20, 28, "Unknown", 1);
        break;
    }

    OLED_Refresh();
}

void OLED_UpdateBattery(uint8_t pct)
{
    /* Redraw battery indicator in top-right corner */
    char buf[8];
    snprintf(buf, sizeof(buf), "%d%%", pct);
    /* In real firmware, update just the battery area */
}