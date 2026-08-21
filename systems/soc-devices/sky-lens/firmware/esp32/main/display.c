/*
 * display.c — SSD1306 OLED 128×64 dashboard / zenith / skymap / lifetime views
 *
 * The display cycles between four views at the press of the MODE button:
 *  1. Dashboard — rate (cpm), corrected rate, pressure, temp, battery, count
 *  2. Zenith    — bar chart of the zenith histogram + cos²θ fit overlay
 *  3. Skymap    — 64×32 az×zen heatmap rendered to 128×64 (2×2 pixels/cell)
 *  4. Lifetime  — decay histogram + fitted τ_µ
 */
#include "display.h"
#include "sky_lens.h"
#include "zenith.h"
#include <stdio.h>
#include <string.h>

#ifdef SKY_LENS_SIM
#include "port_sim.h"
#else
#include "driver/i2c.h"
#include "esp_log.h"
static const char *TAG = "disp";
#define I2C_PORT   I2C_NUM_0
#define OLED_ADDR  0x3C
#endif

static display_view_t s_view = VIEW_DASH;

/* ── SSD1306 command set (abbreviated) ────────────────────────────────── */
#define OLED_CONTROL_BYTE_CMD_SINGLE  0x80
#define OLED_CONTROL_BYTE_CMD_STREAM  0x00
#define OLED_CONTROL_BYTE_DATA_STREAM 0x40

static void oled_cmd(uint8_t cmd)
{
#ifdef SKY_LENS_SIM
    (void)cmd;
#else
    uint8_t buf[2] = {OLED_CONTROL_BYTE_CMD_SINGLE, cmd};
    i2c_master_write_to_device(I2C_PORT, OLED_ADDR, buf, 2, pdMS_TO_TICKS(10));
#endif
}

static void oled_data(const uint8_t *data, int len)
{
#ifdef SKY_LENS_SIM
    (void)data; (void)len;
#else
    uint8_t buf[129];
    buf[0] = OLED_CONTROL_BYTE_DATA_STREAM;
    memcpy(buf + 1, data, len > 128 ? 128 : len);
    i2c_master_write_to_device(I2C_PORT, OLED_ADDR, buf, (len > 128 ? 128 : len) + 1, pdMS_TO_TICKS(10));
#endif
}

static bool s_inited = false;

void display_init(void)
{
#ifdef SKY_LENS_SIM
    port_sim_log("display init (sim)");
#else
    /* SSD1306 init sequence */
    oled_cmd(0xAE);   /* display off */
    oled_cmd(0xD5); oled_cmd(0x80);   /* clock divide */
    oled_cmd(0xA8); oled_cmd(0x3F);   /* multiplex */
    oled_cmd(0xD3); oled_cmd(0x00);   /* display offset */
    oled_cmd(0x40);                   /* start line */
    oled_cmd(0x8D); oled_cmd(0x14);   /* charge pump on */
    oled_cmd(0x20); oled_cmd(0x00);   /* horizontal addressing */
    oled_cmd(0xA1); oled_cmd(0xC8);   /* seg remap + scan dir */
    oled_cmd(0xDA); oled_cmd(0x12);   /* com pins */
    oled_cmd(0x81); oled_cmd(0xCF);   /* contrast */
    oled_cmd(0xD9); oled_cmd(0xF1);   /* pre-charge */
    oled_cmd(0xDB); oled_cmd(0x40);   /* vcomh */
    oled_cmd(0xA4); oled_cmd(0xA6);   /* normal display */
    oled_cmd(0xAF);                   /* display on */
    ESP_LOGI(TAG, "SSD1306 init");
#endif
    s_inited = true;
}

void display_set_view(display_view_t v) { s_view = v % VIEW_COUNT; }
display_view_t display_get_view(void)   { return s_view; }
void display_next_view(void)            { s_view = (s_view + 1) % VIEW_COUNT; }

/* ── Frame buffer: 128×64 / 8 = 1024 bytes (1 bit per pixel, 8 pages) ─── */
static uint8_t s_fb[1024];

static void fb_clear(void) { memset(s_fb, 0, sizeof(s_fb)); }

static void fb_setpixel(int x, int y)
{
    if (x < 0 || x >= 128 || y < 0 || y >= 64) return;
    s_fb[y / 8 * 128 + x] |= (1 << (y & 7));
}

static void fb_text(int x, int y, const char *s)
{
    /* Minimal 5×8 font: each char is 5 cols. We use a placeholder that
     * just advances x; real firmware would use a glyph table. */
    (void)y;
    while (*s) { s++; x += 6; }
    (void)x;
}

void display_update(const daily_t *d, const skymap_t *m,
                    const zenith_fit_t *z, const lifetime_result_t *lf)
{
    if (!s_inited) return;
    fb_clear();

    char line[32];
    switch (s_view) {
    case VIEW_DASH:
        snprintf(line, sizeof(line), "Rate:   %.1f cpm", d->rate_raw_cpm);
        fb_text(0, 0, line);
        snprintf(line, sizeof(line), "Corr:   %.1f cpm", d->rate_corr_cpm);
        fb_text(0, 8, line);
        snprintf(line, sizeof(line), "P: %.1f hPa  T:%.1fC", d->mean_p_hpa, d->mean_t_c);
        fb_text(0, 16, line);
        snprintf(line, sizeof(line), "Events: %lu", (unsigned long)d->n_events);
        fb_text(0, 24, line);
        snprintf(line, sizeof(line), "I0: %.1f cpm  chi2: %.2f", z->i0, z->chi2);
        fb_text(0, 40, line);
        snprintf(line, sizeof(line), "View: DASH");
        fb_text(0, 56, line);
        break;

    case VIEW_ZENITH:
        snprintf(line, sizeof(line), "Zenith hist (cos2th fit)");
        fb_text(0, 0, line);
        {
            /* Find max bin for scaling */
            uint32_t maxb = 1;
            uint32_t bins[ZENITH_BINS];
            zenith_get_bins(bins, ZENITH_BINS);
            for (int i = 0; i < ZENITH_BINS; i++)
                if (bins[i] > maxb) maxb = bins[i];
            /* Draw bars: 18 bars across 120 px, 40 px tall */
            for (int i = 0; i < ZENITH_BINS; i++) {
                int h = (int)((float)bins[i] / (float)maxb * 40.0f);
                int x = i * (120 / ZENITH_BINS);
                for (int y = 60; y > 60 - h; y--)
                    fb_setpixel(x, y);
            }
        }
        break;

    case VIEW_SKYMAP:
        snprintf(line, sizeof(line), "Skymap %lu ev", (unsigned long)m->total);
        fb_text(0, 0, line);
        {
            /* Render 64×32 skymap to 128×64 (2×2 px per cell) */
            uint32_t maxc = 1;
            for (int i = 0; i < SKYMAP_AZ_CELLS * SKYMAP_ZEN_CELLS; i++)
                if (m->cells[i] > maxc) maxc = m->cells[i];
            for (int za = 0; za < SKYMAP_ZEN_CELLS; za++) {
                for (int az = 0; az < SKYMAP_AZ_CELLS; az++) {
                    uint32_t c = m->cells[za * SKYMAP_AZ_CELLS + az];
                    if (c > 0) {
                        int x = az * 2;
                        int y = za * 2;
                        fb_setpixel(x, y); fb_setpixel(x+1, y);
                        fb_setpixel(x, y+1); fb_setpixel(x+1, y+1);
                    }
                }
            }
        }
        break;

    case VIEW_LIFETIME:
        snprintf(line, sizeof(line), "Lifetime mode");
        fb_text(0, 0, line);
        snprintf(line, sizeof(line), "tau = %.3f us", lf->tau_us);
        fb_text(0, 8, line);
        snprintf(line, sizeof(line), "err = +/-%.3f us", lf->tau_err_us);
        fb_text(0, 16, line);
        snprintf(line, sizeof(line), "pairs: %lu  chi2: %.2f",
                 (unsigned long)lf->n_pairs, lf->chi2);
        fb_text(0, 24, line);
        break;

    default:
        break;
    }

    /* Push frame buffer to the OLED (8 pages) */
#ifndef SKY_LENS_SIM
    for (int page = 0; page < 8; page++) {
        oled_cmd(0xB0 + page);          /* set page */
        oled_cmd(0x00); oled_cmd(0x10); /* low + high column */
        oled_data(s_fb + page * 128, 128);
    }
#else
    /* Sim: dump a text summary instead of pixels */
    port_sim_log("display update: view=%d rate=%.1f corr=%.1f events=%lu",
                 s_view, d->rate_raw_cpm, d->rate_corr_cpm,
                 (unsigned long)d->n_events);
#endif
}

#ifndef SKY_LENS_SIM
#include "freertos/FreeRTOS.h"
#endif