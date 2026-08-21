/**
 * display.c — SSD1306 OLED Display Driver for Brew Sense
 * 
 * Renders fermentation data on a 128×32 monochrome OLED.
 * Uses I²C at 0x3C for communication.
 */

#include "display.h"
#include "stm32l4xx_hal.h"
#include <string.h>
#include <stdio.h>

/* SSD1306 commands */
#define SSD1306_SET_DISP        0xAE
#define SSD1306_SET_DISP_ON     0xAF
#define SSD1306_SET_DISP_OFF    0xAE
#define SSD1306_SET_MEM_ADDR    0x20
#define SSD1306_SET_COL_ADDR    0x21
#define SSD1306_SET_PAGE_ADDR   0x22
#define SSD1306_SET_CONTRAST    0x81
#define SSD1306_SET_CHARGE_PUMP 0x8D
#define SSD1306_SET_SEG_REMAP   0xA1
#define SSD1306_SET_COM_SCAN_DIR 0xC8
#define SSD1306_SET_COM_PINS    0xDA
#define SSD1306_SET_VCOM_DESEL  0xDB
#define SSD1306_SET_ENTIRE_ON   0xA5
#define SSD1306_SET_NORM_DISP   0xA6
#define SSD1306_SET_INV_DISP    0xA7
#define SSD1306_SET_MUX_RATIO   0xA8
#define SSD1306_SET_DISP_OFFSET 0xD3
#define SSD1306_SET_DISP_CLK_DIV 0xD5
#define SSD1306_SET_PRECHARGE  0xD9
#define SSD1306_SET_START_LINE  0x40

#define SSD1306_WIDTH   128
#define SSD1306_HEIGHT  32
#define SSD1306_PAGES   (SSD1306_HEIGHT / 8)
#define SSD1306_I2C_ADDR 0x3C

/* Font: 6x8 basic ASCII (minimal, just digits + letters needed) */
extern I2C_HandleTypeDef hi2c1;

/* Display buffer (128 × 32 / 8 = 512 bytes) */
static uint8_t s_framebuf[SSD1306_WIDTH * SSD1306_PAGES];
static bool s_display_on = false;
static display_page_t s_current_page = DISPLAY_PAGE_MAIN;

/*----------------------------------------------------------------------------*/
/* Minimal 5x7 font (digits, period, letters for SG display) */
/*----------------------------------------------------------------------------*/

static const uint8_t font5x7[][5] = {
    /* Space */ {0x00, 0x00, 0x00, 0x00, 0x00},
    /* 0 */ {0x3E, 0x51, 0x49, 0x45, 0x3E},
    /* 1 */ {0x00, 0x42, 0x7F, 0x40, 0x00},
    /* 2 */ {0x42, 0x61, 0x51, 0x49, 0x46},
    /* 3 */ {0x21, 0x41, 0x45, 0x4B, 0x31},
    /* 4 */ {0x18, 0x14, 0x12, 0x7F, 0x10},
    /* 5 */ {0x27, 0x45, 0x45, 0x45, 0x39},
    /* 6 */ {0x3C, 0x4A, 0x49, 0x49, 0x30},
    /* 7 */ {0x01, 0x71, 0x09, 0x05, 0x03},
    /* 8 */ {0x36, 0x49, 0x49, 0x49, 0x36},
    /* 9 */ {0x06, 0x49, 0x49, 0x29, 0x1E},
    /* . */ {0x00, 0x00, 0x60, 0x60, 0x00},
    /* ° */ {0x0C, 0x12, 0x12, 0x0C, 0x00},
    /* A */ {0x7E, 0x11, 0x11, 0x11, 0x7E},
    /* C */ {0x3E, 0x41, 0x41, 0x41, 0x22},
    /* F */ {0x7F, 0x09, 0x09, 0x09, 0x01},
    /* G */ {0x3E, 0x41, 0x49, 0x49, 0x3A},
    /* H */ {0x7F, 0x08, 0x08, 0x08, 0x7F},
    /* K */ {0x7F, 0x08, 0x14, 0x22, 0x41},
    /* L */ {0x7F, 0x40, 0x40, 0x40, 0x40},
    /* O */ {0x3E, 0x41, 0x41, 0x41, 0x3E},
    /* P */ {0x7F, 0x09, 0x09, 0x09, 0x06},
    /* S */ {0x26, 0x49, 0x49, 0x49, 0x32},
    /* T */ {0x01, 0x01, 0x7F, 0x01, 0x01},
    /* V */ {0x7C, 0x02, 0x01, 0x02, 0x7C},
    /* pH */ {0x7F, 0x08, 0x08, 0x08, 0x7F, 0x00, 0x48, 0x44, 0x44, 0x3F}, /* two chars */
};

/*----------------------------------------------------------------------------*/

static void ssd1306_write_cmd(uint8_t cmd) {
    uint8_t buf[2] = {0x00, cmd};  /* Control byte: Co=0, D/C#=0 */
    HAL_I2C_Master_Transmit(&hi2c1, SSD1306_I2C_ADDR << 1, buf, 2, 100);
}

static void ssd1306_write_data(const uint8_t *data, uint16_t len) {
    uint8_t buf[len + 1];
    buf[0] = 0x40;  /* Control byte: Co=0, D/C#=1 */
    memcpy(&buf[1], data, len);
    HAL_I2C_Master_Transmit(&hi2c1, SSD1306_I2C_ADDR << 1, buf, len + 1, 100);
}

/*----------------------------------------------------------------------------*/

int display_init(void) {
    /* Initialize SSD1306 */
    HAL_Delay(100);  /* Display boot time */
    
    ssd1306_write_cmd(SSD1306_SET_DISP_OFF);
    ssd1306_write_cmd(SSD1306_SET_MUX_RATIO);     ssd1306_write_cmd(31);      /* 1/32 duty */
    ssd1306_write_cmd(SSD1306_SET_DISP_OFFSET);    ssd1306_write_cmd(0x00);
    ssd1306_write_cmd(0x40);  /* Set start line = 0 */
    ssd1306_write_cmd(SSD1306_SET_SEG_REMAP);     /* Column address 127 mapped to SEG0 */
    ssd1306_write_cmd(SSD1306_SET_COM_SCAN_DIR);  /* COM0-COM31 */
    ssd1306_write_cmd(SSD1306_SET_COM_PINS);      ssd1306_write_cmd(0x02);
    ssd1306_write_cmd(SSD1306_SET_CONTRAST);       ssd1306_write_cmd(0x8F);   /* Medium contrast */
    ssd1306_write_cmd(SSD1306_SET_ENTIRE_ON);      /* Output follows RAM */
    ssd1306_write_cmd(SSD1306_SET_NORM_DISP);      /* Non-inverted */
    ssd1306_write_cmd(SSD1306_SET_DISP_CLK_DIV);  ssd1306_write_cmd(0x80);   /* Fosc = 8 */
    ssd1306_write_cmd(SSD1306_SET_CHARGE_PUMP);    ssd1306_write_cmd(0x14);   /* Enable charge pump */
    ssd1306_write_cmd(SSD1306_SET_VCOM_DESEL);     ssd1306_write_cmd(0x20);   /* VCOMH = 0.77×Vcc */
    ssd1306_write_cmd(SSD1306_SET_MEM_ADDR);        ssd1306_write_cmd(0x00);   /* Horizontal addressing */
    
    /* Clear display buffer */
    memset(s_framebuf, 0, sizeof(s_framebuf));
    ssd1306_write_data(s_framebuf, sizeof(s_framebuf));
    
    ssd1306_write_cmd(SSD1306_SET_DISP_ON);
    s_display_on = true;
    
    return 0;
}

/*----------------------------------------------------------------------------*/

static void framebuffer_set_pixel(int x, int y, bool on) {
    if (x < 0 || x >= SSD1306_WIDTH || y < 0 || y >= SSD1306_HEIGHT) return;
    
    int page = y / 8;
    int bit = y % 8;
    
    if (on) {
        s_framebuf[page * SSD1306_WIDTH + x] |= (1 << bit);
    } else {
        s_framebuf[page * SSD1306_WIDTH + x] &= ~(1 << bit);
    }
}

static void framebuffer_draw_char(int x, int y, char c, bool large) {
    /* Map character to font index */
    int idx = -1;
    if (c >= '0' && c <= '9') idx = c - '0' + 1;
    else if (c == '.') idx = 11;
    else if (c == 0xB0) idx = 12;  /* degree */
    else if (c == 'A') idx = 13;
    else if (c == 'C') idx = 14;
    else if (c == 'F') idx = 15;
    else if (c == 'G') idx = 16;
    else if (c == 'H') idx = 17;
    else if (c == 'K') idx = 18;
    else if (c == 'L') idx = 19;
    else if (c == 'O') idx = 20;
    else if (c == 'P') idx = 21;
    else if (c == 'S') idx = 22;
    else if (c == 'T') idx = 23;
    else if (c == 'V') idx = 24;
    else if (c == ' ') idx = 0;
    
    if (idx < 0) return;
    
    const uint8_t *glyph = font5x7[idx];
    int scale = large ? 2 : 1;
    
    for (int col = 0; col < 5; col++) {
        for (int row = 0; row < 7; row++) {
            if (glyph[col] & (1 << row)) {
                for (int sx = 0; sx < scale; sx++) {
                    for (int sy = 0; sy < scale; sy++) {
                        framebuffer_set_pixel(x + col * scale + sx,
                                             y + row * scale + sy, true);
                    }
                }
            }
        }
    }
}

static void framebuffer_draw_string(int x, int y, const char *str, bool large) {
    int pos = x;
    while (*str) {
        framebuffer_draw_char(pos, y, *str, large);
        pos += (large ? 12 : 6);
        str++;
    }
}

static void framebuffer_draw_hline(int x1, int x2, int y) {
    for (int x = x1; x <= x2; x++) {
        framebuffer_set_pixel(x, y, true);
    }
}

static void framebuffer_clear(void) {
    memset(s_framebuf, 0, sizeof(s_framebuf));
}

static void framebuffer_flush(void) {
    ssd1306_write_data(s_framebuf, sizeof(s_framebuf));
}

/*----------------------------------------------------------------------------*/

void display_render_main(float gravity, float temperature,
                          ferment_stage_t stage, float activity) {
    framebuffer_clear();
    
    /* Line 1: Large gravity display */
    char sg_str[16];
    snprintf(sg_str, sizeof(sg_str), "SG %.4f", gravity);
    framebuffer_draw_string(0, 0, sg_str, true);  /* Large font */
    
    /* Line 2: Temperature and stage */
    char temp_str[16];
    snprintf(temp_str, sizeof(temp_str), "%.1f C %s", temperature,
             fermentation_stage_str(stage));
    framebuffer_draw_string(0, 18, temp_str, false);  /* Small font */
    
    /* Activity bar (right side, 16px wide) */
    int bar_height = (int)(activity * 30.0f / 100.0f);
    for (int y = 31 - bar_height; y <= 31; y++) {
        framebuffer_draw_hline(120, 127, y);
    }
    
    framebuffer_flush();
}

/*----------------------------------------------------------------------------*/

void display_render_co2_ph(uint16_t co2_ppm, float ph) {
    framebuffer_clear();
    
    char line1[16], line2[16];
    snprintf(line1, sizeof(line1), "CO2: %u ppm", co2_ppm);
    snprintf(line2, sizeof(line2), "pH:  %.2f", ph);
    
    framebuffer_draw_string(0, 0, line1, false);
    framebuffer_draw_string(0, 16, line2, false);
    
    framebuffer_flush();
}

/*----------------------------------------------------------------------------*/

void display_render_graph(const float *gravity_history,
                           uint16_t count, float current_sg) {
    framebuffer_clear();
    
    if (count < 2) {
        framebuffer_draw_string(0, 12, "No data", false);
        framebuffer_flush();
        return;
    }
    
    /* Find min/max for scaling */
    float sg_min = gravity_history[0];
    float sg_max = gravity_history[0];
    for (int i = 1; i < count && i < 48; i++) {
        if (gravity_history[i] < sg_min) sg_min = gravity_history[i];
        if (gravity_history[i] > sg_max) sg_max = gravity_history[i];
    }
    
    /* Add padding */
    sg_min -= 0.001f;
    sg_max += 0.001f;
    float range = sg_max - sg_min;
    if (range < 0.005f) range = 0.005f;
    
    /* Plot gravity history as line graph */
    int x_scale = (SSD1306_WIDTH - 10) / (count > 1 ? count - 1 : 1);
    
    for (int i = 0; i < count - 1 && i < 47; i++) {
        int x1 = 5 + i * x_scale;
        int y1 = (int)(31.0f - (gravity_history[i] - sg_min) / range * 28.0f);
        int x2 = 5 + (i + 1) * x_scale;
        int y2 = (int)(31.0f - (gravity_history[i + 1] - sg_min) / range * 28.0f);
        
        /* Simple line (Bresenham's would be better, but this works) */
        y1 = (y1 < 0) ? 0 : (y1 > 31) ? 31 : y1;
        y2 = (y2 < 0) ? 0 : (y2 > 31) ? 31 : y2;
        
        framebuffer_set_pixel(x1, y1, true);
        framebuffer_set_pixel(x2, y2, true);
    }
    
    /* Show current SG */
    char sg_str[16];
    snprintf(sg_str, sizeof(sg_str), "%.4f", current_sg);
    framebuffer_draw_string(80, 0, sg_str, false);
    
    framebuffer_flush();
}

/*----------------------------------------------------------------------------*/

void display_render_status(uint8_t battery_pct, int8_t wifi_rssi,
                            uint32_t uptime_hours) {
    framebuffer_clear();
    
    char line1[16], line2[16];
    snprintf(line1, sizeof(line1), "BAT: %u%% RSSI:%d", battery_pct, wifi_rssi);
    snprintf(line2, sizeof(line2), "UP: %luh", (unsigned long)uptime_hours);
    
    framebuffer_draw_string(0, 0, line1, false);
    framebuffer_draw_string(0, 16, line2, false);
    
    framebuffer_flush();
}

/*----------------------------------------------------------------------------*/

void display_off(void) {
    ssd1306_write_cmd(SSD1306_SET_DISP_OFF);
    s_display_on = false;
}

void display_on(void) {
    ssd1306_write_cmd(SSD1306_SET_DISP_ON);
    s_display_on = true;
}

bool display_is_on(void) {
    return s_display_on;
}

void display_set_contrast(uint8_t contrast) {
    ssd1306_write_cmd(SSD1306_SET_CONTRAST);
    ssd1306_write_cmd(contrast);
}

void display_next_page(void) {
    s_current_page = (display_page_t)((s_current_page + 1) % 4);
}

display_page_t display_get_page(void) {
    return s_current_page;
}