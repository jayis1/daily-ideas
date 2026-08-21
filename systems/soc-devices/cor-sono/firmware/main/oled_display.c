/*
 * cor-sono / firmware / oled_display.c
 * SSD1306 1.3" 128x64 OLED display driver (SPI)
 * Shows live PCG waveform, heart rate, classification result, battery
 */
#include "main.h"
#include "oled_display.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include <string.h>
#include <stdio.h>

static const char *TAG = "oled";

#define OLED_HOST   SPI2_HOST
#define PIN_CS      10
#define PIN_DC      11
#define PIN_RST     12
#define PIN_CLK     13
#define PIN_MOSI    15

static spi_device_handle_t spi;
static uint8_t fb[128 * 64 / 8];  /* 1 KB framebuffer (page-mode) */

static void oled_cmd(uint8_t cmd)
{
    gpio_set_level(PIN_DC, 0);  /* command mode */
    spi_transaction_t t = { .length = 8, .tx_data = {cmd}, .flags = SPI_TRANS_USE_TXDATA };
    spi_device_polling_transmit(spi, &t);
}

static void oled_data(const uint8_t *data, int len)
{
    gpio_set_level(PIN_DC, 1);  /* data mode */
    spi_transaction_t t = { .length = len * 8, .tx_buffer = data };
    spi_device_polling_transmit(spi, &t);
}

void oled_init(void)
{
    ESP_LOGI(TAG, "init SSD1306 OLED (SPI)");

    spi_bus_config_t buscfg = {
        .miso_io_num = 14, .mosi_io_num = PIN_MOSI, .sclk_io_num = PIN_CLK,
        .max_transfer_sz = 1024,
    };
    spi_bus_initialize(OLED_HOST, &buscfg, SPI_DMA_CH_AUTO);

    spi_device_interface_config_t devcfg = {
        .clock_speed_hz = 8 * 1000 * 1000,
        .mode = 0, .spics_io_num = PIN_CS,
        .queue_size = 7, .flags = SPI_DEVICE_HALFDUPLEX,
    };
    spi_bus_add_device(OLED_HOST, &devcfg, &spi);

    gpio_config_t io = {
        .pin_bit_mask = (1ULL << PIN_DC) | (1ULL << PIN_RST),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&io);

    /* Reset */
    gpio_set_level(PIN_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(PIN_RST, 1);

    /* SSD1306 init sequence */
    oled_cmd(0xAE);  /* display off */
    oled_cmd(0xD5); oled_cmd(0x80);  /* clock divide */
    oled_cmd(0xA8); oled_cmd(0x3F);  /* multiplex 1/64 */
    oled_cmd(0xD3); oled_cmd(0x00);  /* display offset */
    oled_cmd(0x40);  /* start line 0 */
    oled_cmd(0x8D); oled_cmd(0x14);  /* charge pump on */
    oled_cmd(0x20); oled_cmd(0x00);  /* horizontal addressing */
    oled_cmd(0xA1);  /* segment remap */
    oled_cmd(0xC8);  /* COM scan direction */
    oled_cmd(0xDA); oled_cmd(0x12);  /* COM pins */
    oled_cmd(0x81); oled_cmd(0xCF);  /* contrast */
    oled_cmd(0xD9); oled_cmd(0xF1);  /* pre-charge */
    oled_cmd(0xDB); oled_cmd(0x40);  /* VCOM deselect */
    oled_cmd(0xA4);  /* display RAM */
    oled_cmd(0xA6);  /* normal display */
    oled_cmd(0xAF);  /* display on */

    memset(fb, 0, sizeof(fb));
    oled_clear();
    oled_draw_text(0, 0, "Cor Sono", 2);
    oled_draw_text(0, 3, "Smart Stethoscope", 1);
    oled_flush();
}

void oled_clear(void) { memset(fb, 0, sizeof(fb)); }

void oled_flush(void)
{
    for (int p = 0; p < 8; p++) {
        oled_cmd(0xB0 + p);  /* page address */
        oled_cmd(0x00);      /* low col */
        oled_cmd(0x10);      /* high col */
        oled_data(&fb[p * 128], 128);
    }
}

/* Simple 5x7 font (subset) */
static const uint8_t font5x7[][5] = {
    [' '] = {0,0,0,0,0}, ['0']={0x3E,0x51,0x49,0x45,0x3E},
    ['1'] = {0,0x42,0x7F,0x40,0}, ['2']={0x42,0x61,0x51,0x49,0x46},
    ['3'] = {0x21,0x41,0x45,0x4B,0x31}, ['4']={0x18,0x14,0x12,0x7F,0x10},
    ['5'] = {0x27,0x45,0x45,0x45,0x39}, ['6']={0x3C,0x4A,0x49,0x49,0x30},
    ['7'] = {0x01,0x71,0x09,0x05,0x03}, ['8']={0x36,0x49,0x49,0x49,0x36},
    ['9'] = {0x06,0x49,0x49,0x29,0x1E}, [':']={0,0x22,0,0x22,0},
    ['A'] = {0x7E,0x11,0x11,0x11,0x7E}, ['B']={0x7F,0x49,0x49,0x49,0x36},
    ['C'] = {0x3E,0x41,0x41,0x41,0x22}, ['D']={0x7F,0x41,0x41,0x22,0x1C},
    ['E'] = {0x7F,0x49,0x49,0x49,0x41}, ['F']={0x7F,0x09,0x09,0x09,0x01},
    ['G'] = {0x3E,0x41,0x49,0x49,0x7A}, ['H']={0x7F,0x08,0x08,0x08,0x7F},
    ['I'] = {0,0x41,0x7F,0x41,0}, ['L']={0x7F,0x40,0x40,0x40,0x40},
    ['M'] = {0x7F,0x02,0x0C,0x02,0x7F}, ['N']={0x7F,0x04,0x08,0x10,0x7F},
    ['O'] = {0x3E,0x41,0x41,0x41,0x3E}, ['P']={0x7F,0x09,0x09,0x09,0x06},
    ['R'] = {0x7F,0x09,0x19,0x29,0x46}, ['S']={0x46,0x49,0x49,0x49,0x31},
    ['T'] = {0x01,0x01,0x7F,0x01,0x01}, ['U']={0x7F,0x40,0x40,0x40,0x7F},
    ['V'] = {0x7F,0x40,0x40,0x20,0x1F}, ['W']={0x7F,0x20,0x10,0x20,0x7F},
    ['a'] = {0x20,0x54,0x54,0x54,0x78}, ['b']={0x7F,0x48,0x44,0x44,0x38},
    ['c'] = {0x38,0x44,0x44,0x44,0x20}, ['d']={0x38,0x44,0x44,0x48,0x7F},
    ['e'] = {0x38,0x54,0x54,0x54,0x18}, ['g']={0x08,0x14,0x14,0x14,0x7C},
    ['h'] = {0x7F,0x08,0x04,0x04,0x78}, ['i']={0,0x44,0x7D,0x40,0},
    ['k'] = {0x7F,0x10,0x28,0x44,0x40}, ['l']={0,0x41,0x7F,0x40,0},
    ['m'] = {0x7C,0x04,0x18,0x04,0x78}, ['n']={0x7C,0x08,0x04,0x04,0x78},
    ['o'] = {0x38,0x44,0x44,0x44,0x38}, ['r']={0x7C,0x18,0x04,0x04,0x08},
    ['s'] = {0x48,0x54,0x54,0x54,0x24}, ['t']={0x04,0x3F,0x44,0x40,0x20},
    ['u'] = {0x3C,0x40,0x40,0x20,0x7C}, ['w']={0x7C,0x10,0x08,0x10,0x7C},
    ['-'] = {0,0x08,0x08,0x08,0}, ['%']={0x62,0x64,0x08,0x13,0x23},
    ['/'] = {0x20,0x10,0x08,0x04,0x02}, ['.']={0,0x60,0x60,0,0},
};

void oled_draw_text(int x, int y, const char *str, int size)
{
    int col = x;
    while (*str && col < 128 - 5 * size) {
        uint8_t ch = (uint8_t)(*str++);
        if (ch >= 128 || (ch > 'z' && ch != '%')) ch = ' ';
        const uint8_t *glyph = font5x7[ch];
        for (int i = 0; i < 5; i++) {
            uint8_t col_bits = glyph[i];
            for (int row = 0; row < 7; row++) {
                if (col_bits & (1 << row)) {
                    for (int dx = 0; dx < size; dx++)
                        for (int dy = 0; dy < size; dy++) {
                            int px = col + i * size + dx;
                            int py = y * 8 + row * size + dy;
                            if (px < 128 && py < 64)
                                fb[py / 8 * 128 + px] |= (1 << (py % 8));
                        }
                }
            }
        }
        col += 6 * size;
    }
}

/* Draw a waveform in the bottom half of the screen */
void oled_draw_waveform(const int16_t *audio, int n, int y_start, int height)
{
    /* Clear waveform region */
    for (int p = y_start / 8; p <= (y_start + height) / 8; p++)
        memset(&fb[p * 128], 0, 128);

    for (int x = 0; x < 128 && x < n; x++) {
        int idx = x * n / 128;
        int16_t s = audio[idx];
        int y = y_start + height / 2 - (s * height / 2) / 32768;
        if (y < y_start) y = y_start;
        if (y >= y_start + height) y = y_start + height - 1;
        fb[y / 8 * 128 + x] |= (1 << (y % 8));
    }
}

void oled_update_status(int hr, int class_id, int confidence)
{
    char buf[24];
    oled_clear();
    oled_draw_text(0, 0, "Cor Sono", 2);

    /* Heart rate */
    snprintf(buf, sizeof(buf), "HR: %d", hr);
    oled_draw_text(0, 3, buf, 1);

    /* Class + confidence */
    snprintf(buf, sizeof(buf), "%s %d%%", CLASS_NAMES[class_id], confidence);
    oled_draw_text(0, 5, buf, 1);

    /* Battery */
    snprintf(buf, sizeof(buf), "BAT %d%%", g_ctx.battery_pct);
    oled_draw_text(90, 0, buf, 1);

    oled_flush();
}

void oled_show_idle(void)
{
    oled_clear();
    oled_draw_text(0, 0, "Cor Sono", 2);
    oled_draw_text(0, 4, "Press REC", 1);
    oled_draw_text(0, 6, "to start", 1);
    oled_flush();
}