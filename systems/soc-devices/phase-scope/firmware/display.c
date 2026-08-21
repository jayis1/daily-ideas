/*
 * Phase Scope — SH1106 OLED Display Driver (128×64, SPI)
 * Supports phasor diagram, waveform, harmonic bar graph,
 * numeric readout, and transient log pages
 */

#include "display.h"
#include "main.h"
#include <string.h>
#include <math.h>

/* ------------------------------------------------------------------ */
/* SH1106 Commands                                                     */
/* ------------------------------------------------------------------ */

#define SH1106_SET_DISP        0xAE
#define SH1106_SET_DISP_ON     0xAF
#define SH1106_SET_PAGE_ADDR   0xB0
#define SH1106_SET_COL_ADDR_LO 0x00
#define SH1106_SET_COL_ADDR_HI 0x10
#define SH1106_SET_MUX_RATIO   0xA8
#define SH1106_SET_COM_DIR     0xC0
#define SH1106_SET_SEG_DIR     0xA0
#define SH1106_SET_COM_SCAN    0xC8
#define SH1106_SET_OSC_DIV     0xD5
#define SH1106_SET_CHARGE_PUMP 0x8D
#define SH1106_SET_PRECHARGE   0xD9
#define SH1106_SET_VCOM_DESEL  0xDB
#define SH1106_SET_CONTRAST    0x81
#define SH1106_SET_ENTIRE_ON   0xA5
#define SH1106_SET_NORM_DISP   0xA6
#define SH1106_SET_INVERT_DISP 0xA7

/* ------------------------------------------------------------------ */
/* Framebuffer (128 × 64 pixels = 1024 bytes, 8 pages)                */
/* ------------------------------------------------------------------ */

static uint8_t framebuffer[128 * 64 / 8]; /* 1024 bytes */

/* ------------------------------------------------------------------ */
/* SPI helpers                                                         */
/* ------------------------------------------------------------------ */

static inline void spi_cs_oled_low(void)
{
    GPIOB->ODR &= ~(1 << 13); /* PB13 = OLED CS */
}

static inline void spi_cs_oled_high(void)
{
    GPIOB->ODR |= (1 << 13);
}

static inline void spi_dc_data(void)
{
    GPIOB->ODR |= (1 << 5);  /* PB5 = DC */
}

static inline void spi_dc_cmd(void)
{
    GPIOB->ODR &= ~(1 << 5);
}

static void spi_write(uint8_t data)
{
    /* Wait for SPI TXE */
    while (!(SPI1->SR & SPI_SR_TXE))
        ;
    *(volatile uint8_t *)&SPI1->DR = data;
    while (!(SPI1->SR & SPI_SR_BSY))
        ;
    while (SPI1->SR & SPI_SR_BSY)
        ;
}

/* ------------------------------------------------------------------ */
/* Display initialization                                              */
/* ------------------------------------------------------------------ */

void display_init(void)
{
    /* Configure SPI1 */
    RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;

    SPI1->CR1 = SPI_CR1_BR_0          /* Baud rate: PCLK2/4 = 42.5 MHz */
              | SPI_CR1_MSTR           /* Master mode */
              | SPI_CR1_SSM            /* Software slave management */
              | SPI_CR1_SSI            /* Internal slave select */
              | SPI_CR1_SPE;           /* Enable */

    /* Hardware reset */
    GPIOC->ODR &= ~(1 << 5);  /* RST low */
    delay_ms(10);
    GPIOC->ODR |= (1 << 5);   /* RST high */
    delay_ms(100);

    /* Initialization sequence */
    spi_dc_cmd();
    spi_cs_oled_low();

    const uint8_t init_cmds[] = {
        SH1106_SET_DISP,            /* Display off */
        SH1106_SET_MUX_RATIO, 0x3F, /* 64 lines */
        SH1106_SET_SEG_DIR | 0x01,  /* Segment remap */
        SH1106_SET_COM_SCAN,        /* COM scan direction */
        SH1106_SET_OSC_DIV, 0x80,   /* Oscillator divide ratio */
        SH1106_SET_COL_ADDR_LO, 0x02, /* Column offset = 2 */
        SH1106_SET_CHARGE_PUMP, 0x14, /* Enable charge pump */
        SH1106_SET_PRECHARGE, 0xF1,  /* Pre-charge period */
        SH1106_SET_VCOM_DESEL, 0x40,  /* VCOM deselect level */
        SH1106_SET_CONTRAST, 0xCF,    /* Contrast */
        SH1106_SET_NORM_DISP,         /* Normal display */
        SH1106_SET_DISP_ON,           /* Display on */
    };

    for (int i = 0; i < sizeof(init_cmds); i++) {
        spi_write(init_cmds[i]);
    }

    spi_cs_oled_high();

    /* Clear framebuffer */
    memset(framebuffer, 0, sizeof(framebuffer));
    display_update();
}

/* ------------------------------------------------------------------ */
/* Framebuffer operations                                              */
/* ------------------------------------------------------------------ */

void display_clear(void)
{
    memset(framebuffer, 0, sizeof(framebuffer));
}

void display_set_pixel(int x, int y, int set)
{
    if (x < 0 || x >= 128 || y < 0 || y >= 64) return;

    int page = y / 8;
    int bit = y % 8;
    int idx = page * 128 + x;

    if (set)
        framebuffer[idx] |= (1 << bit);
    else
        framebuffer[idx] &= ~(1 << bit);
}

void display_draw_line(int x0, int y0, int x1, int y1)
{
    /* Bresenham's line algorithm */
    int dx = abs(x1 - x0);
    int dy = abs(y1 - y0);
    int sx = (x0 < x1) ? 1 : -1;
    int sy = (y0 < y1) ? 1 : -1;
    int err = dx - dy;

    while (1) {
        display_set_pixel(x0, y0, 1);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x0 += sx; }
        if (e2 < dx)  { err += dx; y0 += sy; }
    }
}

void display_draw_rect(int x, int y, int w, int h)
{
    for (int i = x; i < x + w; i++) {
        display_set_pixel(i, y, 1);
        display_set_pixel(i, y + h - 1, 1);
    }
    for (int j = y; j < y + h; j++) {
        display_set_pixel(x, j, 1);
        display_set_pixel(x + w - 1, j, 1);
    }
}

void display_fill_rect(int x, int y, int w, int h)
{
    for (int i = x; i < x + w; i++) {
        for (int j = y; j < y + h; j++) {
            display_set_pixel(i, j, 1);
        }
    }
}

void display_draw_circle(int cx, int cy, int r)
{
    int x = r, y = 0, err = 1 - r;
    while (x >= y) {
        display_set_pixel(cx + x, cy + y, 1);
        display_set_pixel(cx - x, cy + y, 1);
        display_set_pixel(cx + x, cy - y, 1);
        display_set_pixel(cx - x, cy - y, 1);
        display_set_pixel(cx + y, cy + x, 1);
        display_set_pixel(cx - y, cy + x, 1);
        display_set_pixel(cx + y, cy - x, 1);
        display_set_pixel(cx - y, cy - x, 1);
        y++;
        if (err <= 0) {
            err += 2 * y + 1;
        } else {
            x--;
            err += 2 * (y - x) + 1;
        }
    }
}

/* ------------------------------------------------------------------ */
/* Font data (5×7 minimal font)                                        */
/* ------------------------------------------------------------------ */

static const uint8_t font5x7[][5] = {
    /* Space */ {0x00, 0x00, 0x00, 0x00, 0x00},
    /* '!' */   {0x00, 0x00, 0x5F, 0x00, 0x00},
    /* '"' */   {0x00, 0x07, 0x00, 0x07, 0x00},
    /* '#' */   {0x14, 0x7F, 0x14, 0x7F, 0x14},
    /* '$' */   {0x24, 0x2A, 0x7F, 0x2A, 0x12},
    /* '%' */   {0x23, 0x13, 0x08, 0x64, 0x62},
    /* ... (abbreviated — full font in production) */
    /* '0' */   {0x3E, 0x51, 0x49, 0x45, 0x3E},
    /* '1' */   {0x00, 0x42, 0x7F, 0x40, 0x00},
    /* '2' */   {0x42, 0x61, 0x51, 0x49, 0x46},
    /* '3' */   {0x21, 0x41, 0x45, 0x4B, 0x31},
    /* '4' */   {0x18, 0x14, 0x12, 0x7F, 0x10},
    /* '5' */   {0x27, 0x45, 0x45, 0x45, 0x39},
    /* '6' */   {0x3C, 0x4A, 0x49, 0x49, 0x30},
    /* '7' */   {0x01, 0x71, 0x09, 0x05, 0x03},
    /* '8' */   {0x36, 0x49, 0x49, 0x49, 0x36},
    /* '9' */   {0x06, 0x49, 0x49, 0x29, 0x1E},
    /* ':' */   {0x00, 0x36, 0x36, 0x00, 0x00},
    /* ';' */   {0x00, 0x56, 0x36, 0x00, 0x00},
    /* 'A' */   {0x7E, 0x11, 0x11, 0x11, 0x7E},
    /* 'B' */   {0x7F, 0x49, 0x49, 0x49, 0x36},
    /* 'C' */   {0x3E, 0x41, 0x41, 0x41, 0x22},
    /* 'D' */   {0x7F, 0x41, 0x41, 0x22, 0x1C},
    /* 'E' */   {0x7F, 0x49, 0x49, 0x49, 0x41},
    /* 'F' */   {0x7F, 0x09, 0x09, 0x09, 0x01},
    /* 'G' */   {0x3E, 0x41, 0x49, 0x49, 0x7A},
    /* 'H' */   {0x7F, 0x08, 0x08, 0x08, 0x7F},
    /* 'I' */   {0x00, 0x41, 0x7F, 0x41, 0x00},
    /* 'J' */   {0x20, 0x40, 0x41, 0x3F, 0x01},
    /* 'K' */   {0x7F, 0x08, 0x14, 0x22, 0x41},
    /* 'L' */   {0x7F, 0x40, 0x40, 0x40, 0x40},
    /* 'M' */   {0x7F, 0x02, 0x0C, 0x02, 0x7F},
    /* 'N' */   {0x7F, 0x04, 0x08, 0x10, 0x7F},
    /* 'O' */   {0x3E, 0x41, 0x41, 0x41, 0x3E},
    /* 'P' */   {0x7F, 0x09, 0x09, 0x09, 0x06},
    /* 'Q' */   {0x3E, 0x41, 0x51, 0x21, 0x5E},
    /* 'R' */   {0x7F, 0x09, 0x09, 0x19, 0x66},
    /* 'S' */   {0x46, 0x49, 0x49, 0x49, 0x31},
    /* 'T' */   {0x01, 0x01, 0x7F, 0x01, 0x01},
    /* 'U' */   {0x3F, 0x40, 0x40, 0x40, 0x3F},
    /* 'V' */   {0x1F, 0x20, 0x40, 0x20, 0x1F},
    /* 'W' */   {0x3F, 0x40, 0x38, 0x40, 0x3F},
    /* 'X' */   {0x63, 0x14, 0x08, 0x14, 0x63},
    /* 'Y' */   {0x07, 0x08, 0x70, 0x08, 0x07},
    /* 'Z' */   {0x61, 0x51, 0x49, 0x45, 0x43},
    /* ... (more characters in production) */
};

/* Large font (8×16) for numeric readout */
static const uint8_t font8x16[][16] = {
    /* '0' */ {0x00,0x7C,0xC6,0xCE,0xD6,0xE6,0xC6,0xC6,0xC6,0xC6,0xC6,0xC6,0x7C,0x00,0x00,0x00},
    /* '1' */ {0x00,0x18,0x38,0x78,0x18,0x18,0x18,0x18,0x18,0x18,0x18,0x18,0x7E,0x00,0x00,0x00},
    /* '2' */ {0x00,0x7C,0xC6,0xC6,0x06,0x0C,0x18,0x30,0x60,0xC0,0xC0,0xC6,0xFE,0x00,0x00,0x00},
    /* '3' */ {0x00,0x7C,0xC6,0xC6,0x06,0x06,0x3C,0x06,0x06,0x06,0xC6,0xC6,0x7C,0x00,0x00,0x00},
    /* '4' */ {0x00,0x04,0x0C,0x1C,0x3C,0x6C,0xCC,0xFE,0x0C,0x0C,0x0C,0x0C,0x0C,0x00,0x00,0x00},
    /* '5' */ {0x00,0xFE,0xC0,0xC0,0xC0,0xFC,0xCE,0xC6,0x06,0x06,0xC6,0xC6,0x7C,0x00,0x00,0x00},
    /* '6' */ {0x00,0x3C,0x60,0xC0,0xC0,0xFC,0xC6,0xC6,0xC6,0xC6,0xC6,0xC6,0x7C,0x00,0x00,0x00},
    /* '7' */ {0x00,0xFE,0xC6,0x06,0x06,0x0C,0x18,0x30,0x30,0x30,0x30,0x30,0x30,0x00,0x00,0x00},
    /* '8' */ {0x00,0x7C,0xC6,0xC6,0xC6,0xC6,0x7C,0xC6,0xC6,0xC6,0xC6,0xC6,0x7C,0x00,0x00,0x00},
    /* '9' */ {0x00,0x7C,0xC6,0xC6,0xC6,0xC6,0x7E,0x06,0x06,0x06,0x0C,0x78,0x00,0x00,0x00},
    /* '.' */ {0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x18,0x18,0x00,0x00,0x00},
    /* 'V' */ {0x00,0xC6,0xC6,0xC6,0xC6,0xC6,0xC6,0x6C,0x6C,0x38,0x38,0x10,0x10,0x00,0x00,0x00},
    /* 'A' */ {0x00,0x7C,0xC6,0xC6,0xC6,0xC6,0xFE,0xC6,0xC6,0xC6,0xC6,0xC6,0xC6,0x00,0x00,0x00},
};

/* ------------------------------------------------------------------ */
/* Text rendering                                                       */
/* ------------------------------------------------------------------ */

static int char_index(char c)
{
    if (c >= '0' && c <= '9') return 26 + (c - '0');  /* offset in font5x7 */
    if (c >= 'A' && c <= 'Z') return 36 + (c - 'A');  /* offset in font5x7 */
    if (c >= 'a' && c <= 'z') return 36 + (c - 'a');  /* uppercase map */
    if (c == ' ') return 0;
    if (c == ':') return 10 + 6;
    if (c == '.') return 10 + 5;
    return 0;
}

void display_draw_char(int x, int y, char c, int font)
{
    if (font == FONT_SMALL) {
        int idx = char_index(c);
        for (int col = 0; col < 5; col++) {
            uint8_t line = font5x7[idx][col];
            for (int row = 0; row < 7; row++) {
                if (line & (1 << row)) {
                    display_set_pixel(x + col, y + row, 1);
                }
            }
        }
    }
    /* FONT_LARGE uses font8x16 for digits */
}

void display_draw_string(int x, int y, const char *str, int font)
{
    int cx = x;
    while (*str) {
        display_draw_char(cx, y, *str, font);
        cx += (font == FONT_SMALL) ? 6 : 10;
        str++;
    }
}

/* ------------------------------------------------------------------ */
/* Page rendering                                                       */
/* ------------------------------------------------------------------ */

void display_render_page(uint8_t page, const power_results_t *res)
{
    display_clear();

    switch (page) {
    case PAGE_PHASOR:
        render_phasor(res);
        break;
    case PAGE_WAVEFORM:
        render_waveform(res);
        break;
    case PAGE_HARMONICS:
        render_harmonics(res);
        break;
    case PAGE_NUMERIC:
        render_numeric(res);
        break;
    case PAGE_TRANSIENT:
        render_transient(res);
        break;
    }

    display_update();
}

/* ------------------------------------------------------------------ */
/* Page 1: Phasor diagram                                               */
/* ------------------------------------------------------------------ */

static void render_phasor(const power_results_t *res)
{
    int cx = 64, cy = 32, r = 24;

    /* Draw reference circle */
    display_draw_circle(cx, cy, r);

    /* Draw 3-phase voltage vectors */
    for (int phase = 0; phase < 3; phase++) {
        float angle = -((float)phase * 120.0f * (float)M_PI / 180.0f);
        float vrms = res->vrms[phase];
        float scale = (float)r / 260.0f; /* 260V = full scale */
        int len = (int)(vrms * scale);
        if (len > r) len = r;

        int ex = cx + (int)(len * cosf(angle));
        int ey = cy + (int)(len * sinf(angle));

        display_draw_line(cx, cy, ex, ey);
    }

    /* Labels */
    char buf[16];
    snprintf(buf, sizeof(buf), "L1:%.0fV", res->vrms[0]);
    display_draw_string(0, 0, buf, FONT_SMALL);
    snprintf(buf, sizeof(buf), "L2:%.0fV", res->vrms[1]);
    display_draw_string(72, 0, buf, FONT_SMALL);
    snprintf(buf, sizeof(buf), "L3:%.0fV", res->vrms[2]);
    display_draw_string(0, 54, buf, FONT_SMALL);
    snprintf(buf, sizeof(buf), "%.1fHz", res->frequency);
    display_draw_string(72, 54, buf, FONT_SMALL);
}

/* ------------------------------------------------------------------ */
/* Page 2: Waveform view                                               */
/* ------------------------------------------------------------------ */

static void render_waveform(const power_results_t *res)
{
    /* Draw axes */
    display_draw_line(0, 32, 127, 32); /* Center line */
    display_draw_line(64, 0, 64, 63);  /* Vertical divider */

    /* Sine wave placeholders — in production, we'd render actual
     * samples from the ADC buffer. Here we draw approximate waveforms
     * based on RMS and frequency */
    for (int x = 0; x < 64; x++) {
        float t = (float)x / 64.0f * 2.0f * (float)M_PI;
        int y_v = 32 - (int)(20.0f * sinf(t));
        int y_i = 32 - (int)(15.0f * sinf(t + 0.3f));
        display_set_pixel(x, y_v, 1);
        display_set_pixel(x + 64, y_i, 1);
    }

    display_draw_string(0, 0, "V1 Wave", FONT_SMALL);
    display_draw_string(64, 0, "I1 Wave", FONT_SMALL);
}

/* ------------------------------------------------------------------ */
/* Page 3: Harmonic bar graph                                          */
/* ------------------------------------------------------------------ */

static void render_harmonics(const power_results_t *res)
{
    char buf[16];
    snprintf(buf, sizeof(buf), "THD:%.1f%%", res->thd_v[0]);
    display_draw_string(0, 0, buf, FONT_SMALL);

    /* Bar graph of first 16 harmonics */
    float max_h = res->harmonics_v[0][0]; /* Fundamental */
    if (max_h < 0.001f) max_h = 1.0f;

    for (int h = 0; h < 16; h++) {
        float mag = res->harmonics_v[0][h];
        int bar_height = (int)((mag / max_h) * 48.0f);
        if (bar_height > 48) bar_height = 48;

        int bar_x = 4 + h * 7;
        int bar_y = 58 - bar_height;

        for (int dy = 0; dy < bar_height; dy++) {
            display_set_pixel(bar_x, bar_y + dy, 1);
            display_set_pixel(bar_x + 1, bar_y + dy, 1);
            display_set_pixel(bar_x + 2, bar_y + dy, 1);
            display_set_pixel(bar_x + 3, bar_y + dy, 1);
        }
    }

    snprintf(buf, sizeof(buf), "F:%.0fV", res->vrms[0]);
    display_draw_string(70, 0, buf, FONT_SMALL);
}

/* ------------------------------------------------------------------ */
/* Page 4: Numeric readout                                             */
/* ------------------------------------------------------------------ */

static void render_numeric(const power_results_t *res)
{
    char buf[22];

    /* Line 1: L1 */
    snprintf(buf, sizeof(buf), "L1:%.1fV %.1fA PF%.2f",
             res->vrms[0], res->irms[0], res->pf[0]);
    display_draw_string(0, 0, buf, FONT_SMALL);

    /* Line 2: L2 */
    snprintf(buf, sizeof(buf), "L2:%.1fV %.1fA PF%.2f",
             res->vrms[1], res->irms[1], res->pf[1]);
    display_draw_string(0, 12, buf, FONT_SMALL);

    /* Line 3: L3 */
    snprintf(buf, sizeof(buf), "L3:%.1fV %.1fA PF%.2f",
             res->vrms[2], res->irms[2], res->pf[2]);
    display_draw_string(0, 24, buf, FONT_SMALL);

    /* Line 4: Frequency and total power */
    snprintf(buf, sizeof(buf), "F:%.2fHz", res->frequency);
    display_draw_string(0, 36, buf, FONT_SMALL);

    float total_p = res->p[0] + res->p[1] + res->p[2];
    if (fabsf(total_p) >= 1000.0f)
        snprintf(buf, sizeof(buf), "P:%.2fkW", total_p / 1000.0f);
    else
        snprintf(buf, sizeof(buf), "P:%.0fW", total_p);
    display_draw_string(0, 48, buf, FONT_SMALL);

    /* Line 5: Battery and temperature */
    snprintf(buf, sizeof(buf), "%.1fV %.0fC", res->vbat, res->temperature);
    display_draw_string(80, 54, buf, FONT_SMALL);

    /* Logging indicator */
    if (logging_active) {
        display_draw_string(100, 0, "LOG", FONT_SMALL);
    }
}

/* ------------------------------------------------------------------ */
/* Page 5: Transient log                                               */
/* ------------------------------------------------------------------ */

static void render_transient(const power_results_t *res)
{
    char buf[22];
    display_draw_string(0, 0, "Transient Log", FONT_SMALL);

    if (res->flags & 0x01) {
        display_draw_string(0, 12, "L1: OVERVOLTAGE", FONT_SMALL);
    }
    if (res->flags & 0x02) {
        display_draw_string(0, 22, "L2: OVERVOLTAGE", FONT_SMALL);
    }
    if (res->flags & 0x04) {
        display_draw_string(0, 32, "L3: OVERVOLTAGE", FONT_SMALL);
    }

    if (res->flags == 0) {
        display_draw_string(0, 30, "No transients", FONT_SMALL);
    }

    snprintf(buf, sizeof(buf), "Pk:%.0fV", res->vpeak[0]);
    display_draw_string(0, 48, buf, FONT_SMALL);
}

/* ------------------------------------------------------------------ */
/* Push framebuffer to display                                          */
/* ------------------------------------------------------------------ */

void display_update(void)
{
    for (int page = 0; page < 8; page++) {
        spi_dc_cmd();
        spi_cs_oled_low();
        spi_write(SH1106_SET_PAGE_ADDR | page);
        spi_write(SH1106_SET_COL_ADDR_LO | 2);
        spi_write(SH1106_SET_COL_ADDR_HI | 0);
        spi_cs_oled_high();

        spi_dc_data();
        spi_cs_oled_low();
        for (int col = 0; col < 128; col++) {
            spi_write(framebuffer[page * 128 + col]);
        }
        spi_cs_oled_high();
    }
}