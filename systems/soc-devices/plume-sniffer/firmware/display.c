/* display.c — SSD1306 OLED driver (I2C, 128×64)
 *
 * Minimal I2C bit-bang via ESP-IDF driver. Frame buffer is 128×64 / 8 = 1024 bytes.
 * The chromatogram is plotted as a scrolling waveform in the top 48 pixels;
 * the bottom 16 pixels show status text (8×2 chars at 6×8 font).
 */
#include <string.h>
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "driver/i2c.h"

#include "sdkconfig.h"
#include "display.h"

static const char *TAG = "display";

#define DISP_I2C_HOST   I2C_NUM_0
#define DISP_SDA        1
#define DISP_SCL        1   /* Note: ESP32-C3 shares I2C bus — SCL on separate pin via GPIO */
#define DISP_ADDR       0x3C
#define DISP_WIDTH      128
#define DISP_HEIGHT     64
#define DISP_BUFSZ      (DISP_WIDTH * DISP_HEIGHT / 8)

static uint8_t s_fb[DISP_BUFSZ];

/* We need SCL on a real pin — GPIO0 is BOOT but usable as I2C SCL after boot */
#define DISP_PIN_SCL    0

static void i2c_write_cmd(uint8_t cmd)
{
    i2c_cmd_handle_t h = i2c_cmd_link_create();
    i2c_master_start(h);
    i2c_master_write_byte(h, (DISP_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(h, 0x00, true);   /* Co=0, D/C=0 → command */
    i2c_master_write_byte(h, cmd, true);
    i2c_master_stop(h);
    i2c_master_cmd_begin(DISP_I2C_HOST, h, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(h);
}

static void i2c_write_data(const uint8_t *data, int len)
{
    i2c_cmd_handle_t h = i2c_cmd_link_create();
    i2c_master_start(h);
    i2c_master_write_byte(h, (DISP_ADDR << 1) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(h, 0x40, true);   /* D/C=1 → data */
    i2c_master_write(h, (uint8_t *)data, len, true);
    i2c_master_stop(h);
    i2c_master_cmd_begin(DISP_I2C_HOST, h, pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(h);
}

static void fb_clear(void) { memset(s_fb, 0, DISP_BUFSZ); }

static void fb_set_pixel(int x, int y)
{
    if (x < 0 || x >= DISP_WIDTH || y < 0 || y >= DISP_HEIGHT) return;
    s_fb[(y / 8) * DISP_WIDTH + x] |= (1 << (y & 7));
}

static void fb_draw_text(int x, int y, const char *str)
{
    /* Minimal 5×7 font — just draw a placeholder bar for each char.
     * A real implementation would use a font table. For brevity, we
     * represent text as a row of dots. */
    (void)y;
    for (int i = 0; str[i] && x < DISP_WIDTH - 5; i++, x += 6) {
        for (int dx = 0; dx < 4; dx++)
            fb_set_pixel(x + dx, y + 5);
    }
}

static void fb_flush(void)
{
    for (int page = 0; page < 8; page++) {
        i2c_write_cmd(0xB0 + page);          /* page address */
        i2c_write_cmd(0x00 | (0 & 0x0F));    /* low col */
        i2c_write_cmd(0x10 | (0 >> 4));      /* high col */
        i2c_write_data(&s_fb[page * DISP_WIDTH], DISP_WIDTH);
    }
}

void display_init(void)
{
    ESP_LOGI(TAG, "Initializing SSD1306 OLED (I2C 0x3C)");
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = DISP_SDA,
        .scl_io_num = DISP_PIN_SCL,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = 400000,
    };
    i2c_param_config(DISP_I2C_HOST, &conf);
    i2c_driver_install(DISP_I2C_HOST, I2C_MODE_MASTER, 0, 0, 0);

    /* SSD1306 init sequence */
    i2c_write_cmd(0xAE);  /* display off */
    i2c_write_cmd(0xD5); i2c_write_cmd(0x80);  /* clock div */
    i2c_write_cmd(0xA8); i2c_write_cmd(0x3F);  /* multiplex 1/64 */
    i2c_write_cmd(0xD3); i2c_write_cmd(0x00);  /* display offset */
    i2c_write_cmd(0x40);  /* start line 0 */
    i2c_write_cmd(0x8D); i2c_write_cmd(0x14);  /* charge pump on */
    i2c_write_cmd(0x20); i2c_write_cmd(0x00);  /* addressing mode horizontal */
    i2c_write_cmd(0xA1);  /* seg remap */
    i2c_write_cmd(0xC8);  /* COM scan remap */
    i2c_write_cmd(0xDA); i2c_write_cmd(0x12);  /* COM pins */
    i2c_write_cmd(0x81); i2c_write_cmd(0xCF);  /* contrast */
    i2c_write_cmd(0xD9); i2c_write_cmd(0xF1);  /* precharge */
    i2c_write_cmd(0xDB); i2c_write_cmd(0x40);  /* VCOMH */
    i2c_write_cmd(0xA4);  /* display from RAM */
    i2c_write_cmd(0xA6);  /* normal (not inverted) */
    i2c_write_cmd(0xAF);  /* display ON */

    fb_clear();
    fb_flush();
}

void display_boot(float battery_mv)
{
    fb_clear();
    char buf[32];
    snprintf(buf, sizeof(buf), "PLUME SNIFFER");
    fb_draw_text(0, 0, buf);
    snprintf(buf, sizeof(buf), "BAT %.2fV", battery_mv / 1000.0f);
    fb_draw_text(0, 12, buf);
    fb_flush();
}

void display_menu(int selected)
{
    fb_clear();
    fb_draw_text(0, 0,  "MENU");
    fb_draw_text(0, 10, " RUN");
    fb_draw_text(0, 20, " METHOD");
    fb_draw_text(0, 30, " LIBRARY");
    fb_draw_text(0, 40, " LOG");
    /* Arrow on selected row */
    for (int x = 0; x < 3; x++) {
        fb_set_pixel(x, 12 + selected * 10);
        fb_set_pixel(x, 13 + selected * 10);
        fb_set_pixel(x, 14 + selected * 10);
    }
    fb_flush();
}

void display_running(float col_temp, float target_temp, float prec_temp,
                     int elapsed_s, int total_s, const char *phase)
{
    fb_clear();
    char buf[32];
    snprintf(buf, sizeof(buf), "%s %ds/%d", phase, elapsed_s, total_s);
    fb_draw_text(0, 0, buf);
    snprintf(buf, sizeof(buf), "COL %.0f/%.0fC", col_temp, target_temp);
    fb_draw_text(0, 10, buf);
    snprintf(buf, sizeof(buf), "PREC %.0fC", prec_temp);
    fb_draw_text(0, 20, buf);
    fb_flush();
}

void display_chromatogram_live(const float *trace, int n, int max_n)
{
    fb_clear();
    /* Plot trace in top 48 pixels */
    float max_v = 1.0f;
    for (int i = 0; i < n; i++) {
        float v = trace[i] < 0 ? -trace[i] : trace[i];
        if (v > max_v) max_v = v;
    }
    int plot_w = DISP_WIDTH;
    int plot_h = 48;
    int stride = (n + plot_w - 1) / plot_w;
    for (int x = 0; x < plot_w; x++) {
        int idx = x * stride;
        if (idx >= n) break;
        int h = (int)((trace[idx] / max_v) * (float)plot_h);
        if (h < 0) h = -h;
        for (int y = 0; y < h && y < plot_h; y++)
            fb_set_pixel(x, plot_h - 1 - y);
    }
    /* Bottom 16px: axis label */
    fb_draw_text(0, 52, "TCD uV");
    fb_flush();
}

void display_peak_table(const identification_t *ids, int n, int scroll)
{
    fb_clear();
    char buf[32];
    fb_draw_text(0, 0, "PEAKS");
    for (int i = scroll; i < n && i < scroll + 5; i++) {
        const char *name = ids[i].n_matches > 0
            ? library_get(ids[i].matches[0].index)->name : "???";
        int y = 10 + (i - scroll) * 10;
        snprintf(buf, sizeof(buf), "%.0fs %s %.0fppm",
                 ids[i].retention_s, name, ids[i].est_conc_ppm);
        fb_draw_text(0, y, buf);
    }
    fb_flush();
}

void display_status(const char *msg)
{
    fb_clear();
    fb_draw_text(0, 0, msg);
    fb_flush();
}