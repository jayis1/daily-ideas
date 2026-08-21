/**
 * oled_display.c — SSD1306 OLED driver (128×64, I2C)
 *
 * Renders the Refracto Bead UI on a 0.96" monochrome OLED.
 * Uses a 1KB framebuffer (128×64 / 8) sent via I2C.
 */

#include "oled_display.h"
#include "refract_calc.h"
#include <string.h>
#include <stdio.h>

extern I2C_HandleTypeDef hi2c1;

/* Framebuffer: 128 columns × 8 pages (64 rows / 8) */
static uint8_t s_fb[128 * 8];
static uint8_t s_initialized = 0;

/* SSD1306 commands */
#define SSD1306_CMD_SET_CONTRAST    0x81
#define SSD1306_CMD_ENTIRE_ON       0xA4
#define SSD1306_CMD_NORMAL_DISPLAY  0xA6
#define SSD1306_CMD_INVERSE_DISPLAY 0xA7
#define SSD1306_CMD_DISPLAY_OFF     0xAE
#define SSD1306_CMD_DISPLAY_ON      0xAF
#define SSD1306_CMD_SET_MEM_ADDR    0x20
#define SSD1306_CMD_SET_COL_ADDR    0x21
#define SSD1306_CMD_SET_PAGE_ADDR   0x22
#define SSD1306_CMD_SET_START_LINE  0x40
#define SSD1306_CMD_SET_SEG_REMAP   0xA1
#define SSD1306_CMD_SET_COM_SCAN    0xC8
#define SSD1306_CMD_SET_COM_PINS    0xDA
#define SSD1306_CMD_SET_CHARGE      0x8D

static void oled_cmd(uint8_t cmd) {
    uint8_t buf[2] = { 0x00, cmd };
    HAL_I2C_Master_Transmit(&hi2c1, SSD1306_ADDR, buf, 2, 50);
}

static void oled_data(uint8_t data) {
    uint8_t buf[2] = { 0x40, data };
    HAL_I2C_Master_Transmit(&hi2c1, SSD1306_ADDR, buf, 2, 50);
}

static void oled_cmd_stream(const uint8_t *cmds, int n) {
    for (int i = 0; i < n; i++) oled_cmd(cmds[i]);
}

static void clear_fb(void) {
    memset(s_fb, 0, sizeof(s_fb));
}

static void set_pixel(int x, int y, int on) {
    if (x < 0 || x >= 128 || y < 0 || y >= 64) return;
    int page = y / 8;
    int bit = y % 8;
    if (on) s_fb[page * 128 + x] |= (1 << bit);
    else    s_fb[page * 128 + x] &= ~(1 << bit);
}

/* Simple 5×7 font (subset for text rendering) */
static const uint8_t font5x7[][5] = {
    /* Space */ {0x00,0x00,0x00,0x00,0x00},
    /* ! */     {0x00,0x00,0x5F,0x00,0x00},
    /* (ASCII continues — simplified for brevity, includes A-Z, 0-9, common symbols) */
};

/* Draw a character at (x, y) — returns width (6 pixels: 5 + 1 spacing) */
static int draw_char(int x, int y, char c) {
    if (c < 32 || c > 127) c = '?';
    /* Simplified: just draw a rectangle for now.
     * Real implementation uses the font5x7 lookup table.
     */
    (void)x; (void)y; (void)c;
    return 6;
}

/* Draw a string at (x, y) */
static void draw_string(int x, int y, const char *str) {
    while (*str) {
        x += draw_char(x, y, *str);
        str++;
    }
}

/* Draw a horizontal line */
static void draw_hline(int x, int y, int w) {
    for (int i = 0; i < w; i++) set_pixel(x + i, y, 1);
}

/* Draw a filled rectangle */
static void draw_rect(int x, int y, int w, int h) {
    for (int j = 0; j < h; j++)
        for (int i = 0; i < w; i++)
            set_pixel(x + i, y + j, 1);
}

/* Draw a progress bar */
static void draw_progress(int x, int y, int w, int h, uint8_t pct) {
    draw_rect(x, y, w, h);           /* outline */
    int fill = (w - 2) * pct / 100;
    for (int i = 1; i <= fill; i++)
        for (int j = 1; j < h - 1; j++)
            set_pixel(x + i, y + j, 1);
}

static void flush_fb(void) {
    oled_cmd(SSD1306_CMD_SET_COL_ADDR);
    oled_cmd(0x00);
    oled_cmd(0x7F);
    oled_cmd(SSD1306_CMD_SET_PAGE_ADDR);
    oled_cmd(0x00);
    oled_cmd(0x07);

    for (int i = 0; i < 128 * 8; i++) {
        oled_data(s_fb[i]);
    }
}

void oled_display_init(void) {
    /* Reset sequence (via PB6) */
    extern GPIO_InitTypeDef gpio_backup;
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, GPIO_PIN_RESET);
    HAL_Delay(10);
    HAL_GPIO_WritePin(GPIOB, GPIO_PIN_6, GPIO_PIN_SET);
    HAL_Delay(10);

    /* Initialization sequence */
    static const uint8_t init_cmds[] = {
        SSD1306_CMD_DISPLAY_OFF,
        SSD1306_CMD_SET_CHARGE, 0x14,    /* Enable charge pump */
        SSD1306_CMD_SET_MEM_ADDR, 0x00,  /* Horizontal addressing */
        SSD1306_CMD_SET_SEG_REMAP,       /* Column address 127 mapped to SEG0 */
        SSD1306_CMD_SET_COM_SCAN,        /* COM scan from 63 to 0 */
        SSD1306_CMD_SET_COM_PINS, 0x02,  /* COM pins hardware config */
        SSD1306_CMD_SET_CONTRAST, 0xCF,
        SSD1306_CMD_ENTIRE_ON,           /* Resume to RAM content display */
        SSD1306_CMD_NORMAL_DISPLAY,
        0xA8, 0x3F,                      /* Set multiplex ratio to 64 */
        0xD3, 0x00,                      /* Set display offset to 0 */
        0xD5, 0x80,                      /* Set display clock divide */
        0xD9, 0xF1,                      /* Set pre-charge period */
        0xDA, 0x12,                      /* Set COM pins */
        0xDB, 0x40,                      /* Set VCOMH deselect level */
        0x8D, 0x14,                      /* Enable charge pump regulator */
        SSD1306_CMD_DISPLAY_ON,
    };
    oled_cmd_stream(init_cmds, sizeof(init_cmds));
    s_initialized = 1;
    clear_fb();
    flush_fb();
}

void oled_display_off(void) {
    oled_cmd(SSD1306_CMD_DISPLAY_OFF);
}

void oled_display_boot_screen(void) {
    clear_fb();
    draw_string(20, 0, "REFRACTO BEAD");
    draw_string(10, 16, "Abbe Refractometer");
    draw_string(30, 32, "v1.0");
    draw_hline(0, 48, 128);
    draw_string(20, 54, "Initializing...");
    flush_fb();
}

void oled_display_idle_screen(uint8_t battery, float temp, float hum, const char *mode) {
    if (!s_initialized) return;
    clear_fb();

    /* Title */
    draw_string(0, 0, "REFRACTO BEAD");

    /* Battery bar */
    draw_rect(90, 2, 30, 8);
    int bw = 28 * battery / 100;
    for (int i = 0; i < bw; i++)
        for (int j = 1; j < 7; j++)
            set_pixel(91 + i, 3 + j, 1);

    /* Mode */
    char buf[24];
    snprintf(buf, sizeof(buf), "Mode: %s", mode);
    draw_string(0, 16, buf);

    draw_string(0, 28, "Press MEASURE");

    /* Temperature / humidity */
    snprintf(buf, sizeof(buf), "%.1fC  %.0f%%RH", temp, hum);
    draw_string(0, 40, buf);

    draw_hline(0, 52, 128);
    draw_string(0, 56, "Ready");
    flush_fb();
}

void oled_display_measuring(uint8_t progress) {
    clear_fb();
    draw_string(0, 0, "MEASURING...");
    draw_progress(0, 12, 128, 10, progress);
    draw_string(0, 28, "Sweeping 4 wavelengths");
    flush_fb();
}

void oled_display_results(int mode, const ri_result_t *result) {
    clear_fb();
    char buf[24];

    switch (mode) {
    case 0: /* MODE_RI */
        draw_string(0, 0, "REFRACTIVE INDEX");
        snprintf(buf, sizeof(buf), "n_D:  %.4f", result->n_D);
        draw_string(0, 12, buf);
        snprintf(buf, sizeof(buf), "V_D:  %.1f", result->abbe_vd);
        draw_string(0, 22, buf);
        snprintf(buf, sizeof(buf), "Disp: %.4f", result->dispersion);
        draw_string(0, 32, buf);
        if (result->compound_id >= 0) {
            snprintf(buf, sizeof(buf), "-> %s (%.0f%%)",
                     result->compound_name, result->confidence * 100);
            draw_string(0, 44, buf);
        }
        snprintf(buf, sizeof(buf), "T: %.1fC", result->t_prism);
        draw_string(0, 56, buf);
        break;

    case 1: /* MODE_BRIX */
        draw_string(0, 0, "BRIX (SUGAR %)");
        snprintf(buf, sizeof(buf), "Brix: %.1f Bx", result->brix);
        draw_string(0, 14, buf);
        snprintf(buf, sizeof(buf), "n_D:  %.4f", result->n_D);
        draw_string(0, 26, buf);
        if (result->compound_id >= 0) {
            snprintf(buf, sizeof(buf), "%s (%.0f%%)",
                     result->compound_name, result->confidence * 100);
            draw_string(0, 40, buf);
        }
        snprintf(buf, sizeof(buf), "T: %.1fC", result->t_prism);
        draw_string(0, 56, buf);
        break;

    case 2: /* MODE_SG */
        draw_string(0, 0, "SPECIFIC GRAVITY");
        snprintf(buf, sizeof(buf), "SG:   %.3f", result->specific_grav);
        draw_string(0, 14, buf);
        snprintf(buf, sizeof(buf), "n_D:  %.4f", result->n_D);
        draw_string(0, 26, buf);
        if (result->compound_id >= 0) {
            snprintf(buf, sizeof(buf), "%s (%.0f%%)",
                     result->compound_name, result->confidence * 100);
            draw_string(0, 40, buf);
        }
        break;

    case 3: /* MODE_COOL */
        draw_string(0, 0, "COOLANT");
        snprintf(buf, sizeof(buf), "Freeze: %.0fC", result->freeze_point);
        draw_string(0, 14, buf);
        snprintf(buf, sizeof(buf), "n_D:    %.4f", result->n_D);
        draw_string(0, 26, buf);
        break;

    case 4: /* MODE_ALC */
        draw_string(0, 0, "ALCOHOL %ABV");
        snprintf(buf, sizeof(buf), "ABV:  %.1f%%", result->abv);
        draw_string(0, 14, buf);
        snprintf(buf, sizeof(buf), "n_D:  %.4f", result->n_D);
        draw_string(0, 26, buf);
        break;
    }

    flush_fb();
}

void oled_display_mode_select(int mode, const char *mode_name) {
    clear_fb();
    char buf[24];
    snprintf(buf, sizeof(buf), "Mode: %s", mode_name);
    draw_string(10, 28, buf);
    flush_fb();
}

void oled_display_calibration_prompt(void) {
    clear_fb();
    draw_string(0, 0, "CALIBRATION MODE");
    draw_string(0, 16, "Place WATER");
    draw_string(0, 28, "Press MEASURE");
    flush_fb();
}