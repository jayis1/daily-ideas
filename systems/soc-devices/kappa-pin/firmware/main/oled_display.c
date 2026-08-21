/*
 * kappa-pin / firmware / main / oled_display.c
 * SSD1306 OLED 128x64 display driver (SPI)
 *
 * MIT License.
 */
#include "oled_display.h"
#include "esp_log.h"
#include "driver/spi_master.h"
#include "driver/gpio.h"
#include <string.h>
#include <stdio.h>
#include <math.h>

static const char *TAG = "oled";
static spi_device_handle_t oled_spi;

/* SSD1306 commands */
#define OLED_SET_CONTRAST       0x81
#define OLED_DISPLAY_ON         0xAF
#define OLED_DISPLAY_OFF        0xAE
#define OLED_NORMAL_DISPLAY     0xA6
#define OLED_INVERT_DISPLAY     0xA7
#define OLED_SET_MUX_RATIO      0xA8
#define OLED_SET_OFFSET         0xD3
#define OLED_SET_CHARGE_PUMP    0x8D
#define OLED_SET_VCOMH          0xDB
#define OLED_SET_PRECHARGE      0xD9
#define OLED_SET_SEG_REMAP      0xA1
#define OLED_SET_COM_SCAN_INC   0xC0
#define OLED_SET_COM_SCAN_DEC   0xC8
#define OLED_SET_COMPINS        0xDA
#define OLED_SET_OSC_FREQ       0xD5
#define OLED_SET_COL_ADDR       0x21
#define OLED_SET_PAGE_ADDR      0x22

/* Display buffer: 128x64 = 1024 bytes (8 pages × 128 columns) */
static uint8_t display_buf[1024];
static bool initialized = false;

static void oled_cmd(uint8_t cmd)
{
    gpio_set_level(OLED_DC_PIN, 0);  /* command mode */
    spi_transaction_t t = {0};
    t.length = 8;
    t.tx_buffer = &cmd;
    spi_device_polling_transmit(oled_spi, &t);
}

static void oled_data(uint8_t *data, int len)
{
    gpio_set_level(OLED_DC_PIN, 1);  /* data mode */
    spi_transaction_t t = {0};
    t.length = len * 8;
    t.tx_buffer = data;
    spi_device_polling_transmit(oled_spi, &t);
}

static void oled_reset(void)
{
    gpio_set_level(OLED_RES_PIN, 0);
    vTaskDelay(pdMS_TO_TICKS(50));
    gpio_set_level(OLED_RES_PIN, 1);
    vTaskDelay(pdMS_TO_TICKS(10));
}

static void oled_update(void)
{
    /* Set column address range 0-127 */
    oled_cmd(OLED_SET_COL_ADDR);
    oled_cmd(0);
    oled_cmd(127);

    /* Set page address range 0-7 */
    oled_cmd(OLED_SET_PAGE_ADDR);
    oled_cmd(0);
    oled_cmd(7);

    /* Send display buffer */
    oled_data(display_buf, 1024);
}

static void oled_clear_buf(void)
{
    memset(display_buf, 0, sizeof(display_buf));
}

/* Simple 5x8 font (ASCII 32-127) */
static const uint8_t font5x8[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x5F,0x00,0x00}, /* ! */
    /* ... simplified: use minimal set ... */
};

static void oled_draw_char(int x, int y, char c)
{
    if (c < 32 || c > 127) c = '?';
    int idx = c - 32;
    if (idx >= (int)(sizeof(font5x8)/sizeof(font5x8[0]))) return;
    for (int i = 0; i < 5; i++) {
        uint8_t col = font5x8[idx][i];
        for (int b = 0; b < 8; b++) {
            if (col & (1 << b)) {
                int px = x + i;
                int py = y + b;
                if (px < 128 && py < 64) {
                    display_buf[(py / 8) * 128 + px] |= (1 << (py % 8));
                }
            }
        }
    }
}

static void oled_draw_string(int x, int y, const char *str)
{
    while (*str && x < 123) {
        oled_draw_char(x, y, *str);
        x += 6;
        str++;
    }
}

static void oled_draw_hline(int x1, int x2, int y)
{
    for (int x = x1; x <= x2 && x < 128; x++) {
        display_buf[(y / 8) * 128 + x] |= (1 << (y % 8));
    }
}

static void oled_draw_vline(int x, int y1, int y2)
{
    for (int y = y1; y <= y2 && y < 64; y++) {
        display_buf[(y / 8) * 128 + x] |= (1 << (y % 8));
    }
}

static void oled_set_pixel(int x, int y)
{
    if (x < 0 || x >= 128 || y < 0 || y >= 64) return;
    display_buf[(y / 8) * 128 + x] |= (1 << (y % 8));
}

void oled_init(void)
{
    if (initialized) return;

    /* Configure pins */
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << OLED_CS_PIN) | (1ULL << OLED_DC_PIN) | (1ULL << OLED_RES_PIN),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&io_conf);
    gpio_set_level(OLED_CS_PIN, 1);
    gpio_set_level(OLED_DC_PIN, 0);
    gpio_set_level(OLED_RES_PIN, 1);

    /* Add to SPI bus */
    spi_device_interface_config_t dev_cfg = {
        .clock_speed_hz = 8000000,  /* 8 MHz */
        .mode = 0,
        .spics_io_num = OLED_CS_PIN,
        .queue_size = 4,
    };
    spi_bus_add_device(SPI_HOST, &dev_cfg, &oled_spi);

    /* Reset and initialize */
    oled_reset();
    vTaskDelay(pdMS_TO_TICKS(100));

    oled_cmd(OLED_DISPLAY_OFF);
    oled_cmd(OLED_SET_MUX_RATIO);  oled_cmd(0x3F);
    oled_cmd(OLED_SET_OFFSET);     oled_cmd(0x00);
    oled_cmd(OLED_SET_CHARGE_PUMP); oled_cmd(0x14);  /* enable charge pump */
    oled_cmd(OLED_SET_SEG_REMAP);  /* A1: column 127 = SEG0 */
    oled_cmd(OLED_SET_COM_SCAN_DEC); /* C8: remap rows */
    oled_cmd(OLED_SET_COMPINS);    oled_cmd(0x12);
    oled_cmd(OLED_SET_CONTRAST);   oled_cmd(0xCF);
    oled_cmd(OLED_SET_PRECHARGE);  oled_cmd(0xF1);
    oled_cmd(OLED_SET_VCOMH);      oled_cmd(0x40);
    oled_cmd(OLED_SET_OSC_FREQ);   oled_cmd(0x80);
    oled_cmd(OLED_NORMAL_DISPLAY);
    oled_cmd(OLED_DISPLAY_ON);

    oled_clear_buf();
    oled_update();

    initialized = true;
    ESP_LOGI(TAG, "SSD1306 OLED initialized");
}

void oled_clear(void)
{
    oled_clear_buf();
    oled_update();
}

void oled_show_idle(float temp_c, material_t mat, const char *probe_name)
{
    oled_clear_buf();
    oled_draw_string(0, 0, "Kappa Pin");
    oled_draw_string(0, 12, "Ready");
    char buf[24];
    snprintf(buf, sizeof(buf), "T: %.2f C", temp_c);
    oled_draw_string(0, 24, buf);
    snprintf(buf, sizeof(buf), "Mat: %d", (int)mat);
    oled_draw_string(0, 36, buf);
    oled_draw_string(0, 48, probe_name);
    oled_draw_string(0, 56, "[MEASURE]");
    oled_update();
}

void oled_show_arming(float temp_c, float drift, bool ready)
{
    oled_clear_buf();
    oled_draw_string(0, 0, "Equilibrium");
    char buf[24];
    snprintf(buf, sizeof(buf), "T: %.3f C", temp_c);
    oled_draw_string(0, 16, buf);
    snprintf(buf, sizeof(buf), "drift: %.4f K/s", drift);
    oled_draw_string(0, 28, buf);
    oled_draw_string(0, 48, ready ? "READY" : "wait...");
    oled_update();
}

void oled_show_measuring(float t_elapsed, float dt_mk, float q_w, float target_q)
{
    oled_clear_buf();
    oled_draw_string(0, 0, "Measuring...");
    char buf[24];
    snprintf(buf, sizeof(buf), "t: %.1f s", t_elapsed);
    oled_draw_string(0, 16, buf);
    snprintf(buf, sizeof(buf), "dT: %.0f mK", dt_mk);
    oled_draw_string(0, 28, buf);
    snprintf(buf, sizeof(buf), "Q: %.2f/%.2f W", q_w, target_q);
    oled_draw_string(0, 40, buf);
    oled_update();
}

void oled_show_result(const meas_result_t *r)
{
    oled_clear_buf();
    oled_draw_string(0, 0, "Result");
    char buf[24];
    snprintf(buf, sizeof(buf), "L: %.4f W/mK", r->lambda);
    oled_draw_string(0, 12, buf);
    snprintf(buf, sizeof(buf), "a: %.3f mm2/s", r->alpha);
    oled_draw_string(0, 24, buf);
    snprintf(buf, sizeof(buf), "rhoCp: %.2e", r->rho_cp);
    oled_draw_string(0, 36, buf);
    snprintf(buf, sizeof(buf), "R2: %.5f", r->r_squared);
    oled_draw_string(0, 48, buf);
    oled_draw_string(0, 56, "[MENU] [MEASURE]");
    oled_update();
}

void oled_show_menu(int item, const char **items, int n_items)
{
    oled_clear_buf();
    oled_draw_string(0, 0, "Menu");
    for (int i = 0; i < n_items && i < 7; i++) {
        int y = 12 + i * 8;
        if (i == item) {
            oled_draw_string(0, y, ">");
        }
        oled_draw_string(6, y, items[i]);
    }
    oled_update();
}

void oled_draw_dt_curve(const meas_sample_t *samples, int count, int window_start)
{
    oled_clear_buf();
    oled_draw_string(0, 0, "dT curve");
    /* Draw axes */
    oled_draw_hline(8, 120, 56);
    oled_draw_vline(8, 8, 56);

    if (count < 2) { oled_update(); return; }

    /* Find max ΔT for scaling */
    float dt_max = 0;
    for (int i = 0; i < count; i++) {
        if (samples[i].dt_mk > dt_max) dt_max = samples[i].dt_mk;
    }
    if (dt_max < 1.0f) dt_max = 1.0f;

    /* Plot points */
    for (int i = 0; i < count && i < 110; i++) {
        int x = 10 + i;
        int y = 56 - (int)((samples[i].dt_mk / dt_max) * 46.0f);
        if (y < 8) y = 8;
        if (y > 56) y = 56;
        oled_set_pixel(x, y);
    }
    oled_update();
}

void oled_draw_ln_t_fit(const meas_sample_t *samples, int count,
                         int fit_start, int fit_end, float slope, float intercept)
{
    oled_draw_dt_curve(samples, count, 0);

    /* Draw fit line over regression window */
    if (fit_end > fit_start && fit_end < count) {
        for (int i = fit_start; i <= fit_end && i < 110; i++) {
            float dt_max = 0;
            for (int j = 0; j < count; j++)
                if (samples[j].dt_mk > dt_max) dt_max = samples[j].dt_mk;
            if (dt_max < 1.0f) dt_max = 1.0f;

            float ln_t = logf(samples[i].t_s > 0 ? samples[i].t_s : 0.001f);
            float dt_fit = (slope * ln_t + intercept) * 1000.0f;  /* back to mK */
            int x = 10 + i;
            int y = 56 - (int)((dt_fit / dt_max) * 46.0f);
            if (y >= 8 && y <= 56)
                oled_set_pixel(x, y);
        }
    }
    oled_update();
}