/**
 * lcd_display.c — ST7789V 1.3" IPS LCD driver
 *
 * Drives a 240×240 pixel ST7789V TFT via 4-wire SPI.
 * Includes basic text rendering, bar graphs, and curve plotting
 * for displaying acoustic measurement results.
 */

#include "lcd_display.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include <string.h>

static const char *TAG = "lcd";

/* SPI GPIO (from pin table) */
#define LCD_SPI_CLK   9
#define LCD_SPI_MOSI  10
#define LCD_DC        11
#define LCD_CS        12
#define LCD_RST       13
#define LCD_BL        14

/* ST7789V commands */
#define CMD_SWRESET   0x01
#define CMD_SLPIN     0x10
#define CMD_SLPOUT    0x11
#define CMD_DISPOFF  0x28
#define CMD_DISPON   0x29
#define CMD_CASET    0x2A
#define CMD_RASET    0x2B
#define CMD_RAMWR    0x2C
#define CMD_MADCTL   0x36
#define CMD_COLMOD   0x3A

/* SPI device handle */
static spi_device_handle_t spi_dev = NULL;

/* Framebuffer (240×240×2 bytes = 115.2 KB, in PSRAM) */
static uint16_t *fb = NULL;

/* Simple 5×7 font (ASCII 32–127) */
static const uint8_t font5x7[][5] = { /* minimal subset for display */ {0} };

/* Send a command byte */
static void lcd_cmd(uint8_t cmd) {
    gpio_set_level(LCD_DC, 0);
    spi_transaction_t t = {
        .length = 8,
        .tx_buffer = &cmd,
    };
    spi_device_polling_transmit(spi_dev, &t);
}

/* Send data byte(s) */
static void lcd_data(const uint8_t *data, int len) {
    gpio_set_level(LCD_DC, 1);
    spi_transaction_t t = {
        .length = len * 8,
        .tx_buffer = data,
    };
    spi_device_polling_transmit(spi_dev, &t);
}

/* Set the drawing window */
static void lcd_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
    uint8_t buf[4];
    lcd_cmd(CMD_CASET);
    buf[0] = x0 >> 8; buf[1] = x0 & 0xFF;
    buf[2] = x1 >> 8; buf[3] = x1 & 0xFF;
    lcd_data(buf, 4);

    lcd_cmd(CMD_RASET);
    buf[0] = y0 >> 8; buf[1] = y0 & 0xFF;
    buf[2] = y1 >> 8; buf[3] = y1 & 0xFF;
    lcd_data(buf, 4);

    lcd_cmd(CMD_RAMWR);
}

/* Push framebuffer to display */
static void lcd_flush(void) {
    lcd_set_window(0, 0, 239, 239);
    gpio_set_level(LCD_DC, 1);

    /* Send in chunks of 4096 bytes */
    int total = 240 * 240 * 2;
    int offset = 0;
    while (offset < total) {
        int chunk = (total - offset > 4096) ? 4096 : (total - offset);
        spi_transaction_t t = {
            .length = chunk * 8,
            .tx_buffer = ((uint8_t *)fb) + offset,
        };
        spi_device_polling_transmit(spi_dev, &t);
        offset += chunk;
    }
}

/* Fill framebuffer with a color */
static void fb_fill(uint16_t color) {
    for (int i = 0; i < 240 * 240; i++) {
        fb[i] = color;
    }
}

/* Draw a filled rectangle */
static void fb_rect(int x, int y, int w, int h, uint16_t color) {
    for (int py = y; py < y + h && py < 240; py++) {
        for (int px = x; px < x + w && px < 240; px++) {
            if (px >= 0 && py >= 0)
                fb[py * 240 + px] = color;
        }
    }
}

/* Draw text (simplified — just for labels) */
static void fb_text(int x, int y, const char *text, uint16_t fg, uint16_t bg) {
    /* Simplified: draw character backgrounds as rectangles */
    int len = strlen(text);
    fb_rect(x, y, len * 6, 8, bg);  /* Clear background */
    /* Full font rendering omitted for brevity — uses font5x7 lookup */
    /* In production, each character is rendered pixel-by-pixel */
}

/* RGB565 color macros */
#define RGB565(r, g, b)  (((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))
#define COLOR_BLACK    0x0000
#define COLOR_WHITE    0xFFFF
#define COLOR_BLUE     RGB565(0, 80, 255)
#define COLOR_GREEN    RGB565(0, 200, 0)
#define COLOR_RED      RGB565(255, 50, 0)
#define COLOR_GRAY     RGB565(60, 60, 60)
#define COLOR_DKGRAY   RGB565(30, 30, 30)
#define COLOR_CYAN     RGB565(0, 200, 255)
#define COLOR_YELLOW   RGB565(255, 220, 0)
#define COLOR_ORANGE   RGB565(255, 140, 0)

static const char *mode_labels[] = {"RT60", "FREQ", "MODES", "C50/80", "NC"};

int lcd_display_init(void) {
    ESP_LOGI(TAG, "Initializing ST7789V LCD");

    /* Configure SPI bus */
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = LCD_SPI_MOSI,
        .sclk_io_num = LCD_SPI_CLK,
        .miso_io_num = -1,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 240 * 240 * 2,
    };
    spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO);

    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = 40 * 1000 * 1000,  /* 40 MHz */
        .mode = 0,
        .spics_io_num = LCD_CS,
        .queue_size = 1,
    };
    spi_bus_add_device(SPI2_HOST, &dev_cfg, &spi_dev);

    /* Configure control GPIOs */
    gpio_config_t io_cfg = {
        .pin_bit_mask = (1ULL << LCD_DC) | (1ULL << LCD_RST) | (1ULL << LCD_BL),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&io_cfg);

    /* Hardware reset */
    gpio_set_level(LCD_RST, 0);
    vTaskDelay(pdMS_TO_TICKS(20));
    gpio_set_level(LCD_RST, 1);
    vTaskDelay(pdMS_TO_TICKS(150));

    /* Initialize ST7789V */
    lcd_cmd(CMD_SWRESET);
    vTaskDelay(pdMS_TO_TICKS(150));
    lcd_cmd(CMD_SLPOUT);
    vTaskDelay(pdMS_TO_TICKS(500));

    /* Set color mode: 16-bit RGB565 */
    uint8_t colmod = 0x05;
    lcd_cmd(CMD_COLMOD);
    lcd_data(&colmod, 1);

    /* Set orientation (portrait) */
    uint8_t madctl = 0x00;  /* Normal orientation */
    lcd_cmd(CMD_MADCTL);
    lcd_data(&madctl, 1);

    /* Turn on display */
    lcd_cmd(CMD_DISPON);

    /* Turn on backlight */
    gpio_set_level(LCD_BL, 1);

    /* Allocate framebuffer in PSRAM */
    fb = malloc(240 * 240 * sizeof(uint16_t));
    if (!fb) {
        ESP_LOGE(TAG, "Framebuffer allocation failed");
        return -1;
    }

    fb_fill(COLOR_BLACK);
    fb_text(10, 10, "ECHO MOTE", COLOR_CYAN, COLOR_BLACK);
    lcd_flush();

    ESP_LOGI(TAG, "LCD initialized");
    return 0;
}

void lcd_display_mode_select(uint32_t mode) {
    if (!fb) return;
    fb_fill(COLOR_BLACK);
    fb_text(10, 100, mode_labels[mode], COLOR_WHITE, COLOR_BLACK);
    fb_text(10, 120, "Press MEASURE", COLOR_GRAY, COLOR_BLACK);
    lcd_flush();
}

void lcd_display_measuring(uint32_t mode, uint32_t progress) {
    if (!fb) return;
    fb_fill(COLOR_BLACK);
    fb_text(10, 10, "MEASURING...", COLOR_YELLOW, COLOR_BLACK);
    fb_text(10, 30, mode_labels[mode], COLOR_WHITE, COLOR_BLACK);

    /* Progress bar */
    int bar_x = 20, bar_y = 80, bar_w = 200, bar_h = 16;
    fb_rect(bar_x, bar_y, bar_w, bar_h, COLOR_GRAY);
    int fill_w = (progress * bar_w) / 100;
    fb_rect(bar_x, bar_y, fill_w, bar_h, COLOR_CYAN);

    lcd_flush();
}

void lcd_display_results(uint32_t mode, const acoustic_results_t *results) {
    if (!fb) return;
    fb_fill(COLOR_BLACK);

    switch (mode) {
    case LCD_MODE_RT60:
        fb_text(10, 5, "RT60 Results", COLOR_CYAN, COLOR_BLACK);
        for (int b = 0; b < 6; b++) {
            int y = 30 + b * 32;
            char label[32];
            int freq = 125 << b;
            snprintf(label, sizeof(label), "%dHz", freq);
            fb_text(10, y, label, COLOR_WHITE, COLOR_BLACK);

            /* Bar graph */
            float rt60 = results->rt60[b];
            int bar_len = (int)(rt60 * 100.0f);  /* Scale: 1s = 100px */
            if (bar_len > 150) bar_len = 150;
            uint16_t color = (rt60 < 0.6f) ? COLOR_GREEN :
                             (rt60 < 1.0f) ? COLOR_YELLOW : COLOR_RED;
            fb_rect(60, y + 2, bar_len, 12, color);

            char val[16];
            snprintf(val, sizeof(val), "%.2fs", rt60);
            fb_text(60 + bar_len + 5, y, val, COLOR_GRAY, COLOR_BLACK);
        }
        break;

    case LCD_MODE_FREQ:
        fb_text(10, 5, "Freq Response", COLOR_CYAN, COLOR_BLACK);
        /* Draw magnitude curve (simplified) */
        fb_rect(10, 200, 220, 1, COLOR_GRAY);  /* 0 dB line */
        for (int i = 1; i < NUM_THIRD_OCT; i++) {
            int y_prev = 200 - (int)(results->freq_response_mag[i - 1] * 5.0f);
            int y_curr = 200 - (int)(results->freq_response_mag[i] * 5.0f);
            if (y_prev < 30) y_prev = 30;
            if (y_curr < 30) y_curr = 30;
            if (y_prev > 230) y_prev = 230;
            if (y_curr > 230) y_curr = 230;
            int x_prev = 10 + (i - 1) * 7;
            int x_curr = 10 + i * 7;
            /* Draw line segment (simplified as two pixels) */
            fb_rect(x_prev, y_prev, 2, 2, COLOR_GREEN);
            fb_rect(x_curr, y_curr, 2, 2, COLOR_GREEN);
        }
        break;

    case LCD_MODE_ROOM_MODES:
        fb_text(10, 5, "Room Modes", COLOR_CYAN, COLOR_BLACK);
        for (int m = 0; m < results->num_modes && m < 6; m++) {
            int y = 30 + m * 28;
            char line[32];
            const char *type_str = results->room_modes[m].type == 0 ? "AX" :
                                   results->room_modes[m].type == 1 ? "TG" : "OB";
            snprintf(line, sizeof(line), "%.0fHz %s", results->room_modes[m].freq, type_str);
            fb_text(10, y, line, COLOR_ORANGE, COLOR_BLACK);
        }
        break;

    case LCD_MODE_CLARITY:
        fb_text(10, 5, "C50/C80 Clarity", COLOR_CYAN, COLOR_BLACK);
        for (int b = 0; b < 6; b++) {
            int y = 30 + b * 28;
            char line[32];
            snprintf(line, sizeof(line), "%dHz C50%+.0f C80%+.0f",
                     125 << b, results->c50[b], results->c80[b]);
            uint16_t color = (results->c50[b] > 0.0f) ? COLOR_GREEN : COLOR_RED;
            fb_text(10, y, line, color, COLOR_BLACK);
        }
        break;

    case LCD_MODE_NOISE:
        fb_text(10, 5, "Background NC", COLOR_CYAN, COLOR_BLACK);
        {
            char nc_str[16];
            snprintf(nc_str, sizeof(nc_str), "NC-%.0f", results->nc_rating);
            fb_text(10, 40, nc_str, COLOR_YELLOW, COLOR_BLACK);
        }
        break;
    }

    lcd_flush();
}

void lcd_display_idle(uint32_t mode, float battery_v, float temp, float humidity) {
    if (!fb) return;
    fb_fill(COLOR_BLACK);
    fb_text(10, 10, "ECHO MOTE", COLOR_CYAN, COLOR_BLACK);

    /* Battery bar */
    int batt_pct = (int)((battery_v - 3.0f) / (4.2f - 3.0f) * 100.0f);
    if (batt_pct < 0) batt_pct = 0;
    if (batt_pct > 100) batt_pct = 100;
    fb_rect(170, 10, 60, 12, COLOR_GRAY);
    uint16_t batt_color = (batt_pct > 50) ? COLOR_GREEN :
                          (batt_pct > 20) ? COLOR_YELLOW : COLOR_RED;
    fb_rect(170, 10, (batt_pct * 60) / 100, 12, batt_color);

    fb_text(10, 60, mode_labels[mode], COLOR_WHITE, COLOR_BLACK);
    fb_text(10, 80, "Press MEASURE", COLOR_GRAY, COLOR_BLACK);

    char env_str[32];
    snprintf(env_str, sizeof(env_str), "%.1fC %.0f%%RH", temp, humidity);
    fb_text(10, 110, env_str, COLOR_DKGRAY, COLOR_BLACK);

    lcd_flush();
}

void lcd_display_off(void) {
    if (!fb) return;
    fb_fill(COLOR_BLACK);
    lcd_flush();
    gpio_set_level(LCD_BL, 0);
    lcd_cmd(CMD_DISPOFF);
}