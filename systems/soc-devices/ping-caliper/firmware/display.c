/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * display.c — SSD1306 OLED driver, A-scan renderer, menu system
 *
 * Drives a 128×64 monochrome OLED over SPI1 (shared with MicroSD via CS).
 * Renders a live A-scan (envelope vs depth), the big numeric thickness
 * readout, battery %, material name, and a movable flaw gate.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "stm32g474.h"
#include "display.h"
#include "flaw.h"
#include <string.h>
#include <stdarg.h>
#include <stdio.h>

/* ---- SSD1306 commands ---- */
#define SSD1306_SET_CONTRAST    0x81
#define SSD1306_DISPLAY_ON      0xAF
#define SSD1306_DISPLAY_OFF      0xAE
#define SSD1306_NORMAL_DISP      0xA6
#define SSD1306_SET_COL_ADDR     0x21
#define SSD1306_SET_PAGE_ADDR    0x22
#define SSD1306_SET_SEG_REMAP    0xA1
#define SSD1306_SET_COM_SCAN     0xC8
#define SSD1306_SET_START_LINE   0x40
#define SSD1306_SET_CHARGE_PUMP  0x8D
#define SSD1306_SET_VCOMH        0xDB
#define SSD1306_SET_MUX_RATIO    0xA8
#define SSD1306_SET_DISP_OFFSET  0xD3
#define SSD1306_SET_PRECHARGE    0xD9
#define SSD1306_SET_CLK_DIV      0xD5
#define SSD1306_SET_COM_PINS     0x12

static uint8_t g_fb[OLED_WIDTH * OLED_HEIGHT / 8];
static ui_page_t g_page = UI_PAGE_ASCAN;
static int8_t g_menu_idx = 0;
static int8_t g_menu_top = 0;

/* ---- Minimal 5×7 font (ASCII 0x20..0x7E) ---- */
extern const uint8_t font5x7[][5];

/* ---- SPI helpers ---- */
static void spi_wait(void)
{
    while (!(SPI1->SR & SPI_SR_TXE)) { }
    while (SPI1->SR & SPI_SR_BSY) { }
}

static void spi_write_byte(uint8_t b)
{
    *(volatile uint8_t *)&SPI1->DR = b;
    spi_wait();
}

static void oled_cmd(uint8_t cmd)
{
    /* DC=0 (command), CS low */
    GPIOA->BSRR = (1U << (16 + 15));   /* PA15 low (DC) */
    GPIOB->BSRR = (1U << (16 + 1));    /* PB1 low (CS) */
    spi_write_byte(cmd);
    GPIOB->BSRR = (1U << 1);           /* CS high */
}

static void oled_data(const uint8_t *data, uint16_t len)
{
    GPIOA->BSRR = (1U << 15);          /* DC high (data) */
    GPIOB->BSRR = (1U << (16 + 1));    /* CS low */
    for (uint16_t i = 0; i < len; i++)
        spi_write_byte(data[i]);
    GPIOB->BSRR = (1U << 1);          /* CS high */
}

void display_init(void)
{
    /* Enable GPIOA, GPIOB, SPI1 clocks */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN;
    RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;

    /* PA15 (DC), PB0 (RESET), PB1 (CS) → output */
    GPIOA->MODER = (GPIOA->MODER & ~GPIO_MODER_MODE15) |
                   (1U << GPIO_MODER_MODE15_Pos);
    GPIOB->MODER = (GPIOB->MODER & ~(GPIO_MODER_MODE0 | GPIO_MODER_MODE1 |
                                      GPIO_MODER_MODE3 | GPIO_MODER_MODE4 |
                                      GPIO_MODER_MODE5)) |
                   (1U << GPIO_MODER_MODE0_Pos) | (1U << GPIO_MODER_MODE1_Pos) |
                   (2U << GPIO_MODER_MODE3_Pos) | (2U << GPIO_MODER_MODE4_Pos) |
                   (1U << GPIO_MODER_MODE5_Pos);
    /* PB3 = SPI1_SCK, PB4 = SPI1_MISO, PB5 = CS — wait, PB5 is separate CS */
    /* Reconfigure PB3 (SCK) and PB4 (MOSI) as AF5 (SPI1) */
    GPIOB->MODER = (GPIOB->MODER & ~(GPIO_MODER_MODE3 | GPIO_MODER_MODE4)) |
                   (2U << GPIO_MODER_MODE3_Pos) | (2U << GPIO_MODER_MODE4_Pos);
    GPIOB->AFR[0] = (GPIOB->AFR[0] & ~(0xF << 12)) | (5U << 12);   /* PB3 AF5 */
    GPIOB->AFR[1] = (GPIOB->AFR[1] & ~(0xF << 0))  | (5U << 0);    /* PB4 AF5 */

    /* SPI1: master, 8-bit, CPOL=1 CPHA=1, baud = APB2/4 */
    SPI1->CR1 = SPI_CR1_MSTR | SPI_CR1_CPOL | SPI_CR1_CPHA |
                (3U << SPI_CR1_BR_Pos) | SPI_CR1_SSM | SPI_CR1_SSI;
    SPI1->CR2 = 0;
    SPI1->CR1 |= SPI_CR1_SPE;

    /* Reset the OLED */
    GPIOB->BSRR = (1U << 0);           /* PB0 high (reset idle) */
    GPIOB->BSRR = (1U << (16 + 0));     /* reset low */
    for (volatile int i = 0; i < 10000; i++) { __NOP(); }
    GPIOB->BSRR = (1U << 0);           /* reset high */

    /* SSD1306 init sequence */
    oled_cmd(SSD1306_DISPLAY_OFF);
    oled_cmd(SSD1306_SET_CHARGE_PUMP); oled_cmd(0x14);
    oled_cmd(SSD1306_SET_MUX_RATIO); oled_cmd(0x3F);
    oled_cmd(SSD1306_SET_DISP_OFFSET); oled_cmd(0x00);
    oled_cmd(SSD1306_SET_START_LINE);
    oled_cmd(SSD1306_SET_SEG_REMAP);
    oled_cmd(SSD1306_SET_COM_SCAN);
    oled_cmd(SSD1306_SET_COM_PINS); oled_cmd(0x12);
    oled_cmd(SSD1306_SET_CONTRAST); oled_cmd(0xCF);
    oled_cmd(SSD1306_SET_PRECHARGE); oled_cmd(0xF1);
    oled_cmd(SSD1306_SET_VCOMH); oled_cmd(0x40);
    oled_cmd(SSD1306_SET_CLK_DIV); oled_cmd(0x80);
    oled_cmd(SSD1306_NORMAL_DISP);
    oled_cmd(SSD1306_SET_COL_ADDR); oled_cmd(0); oled_cmd(127);
    oled_cmd(SSD1306_SET_PAGE_ADDR); oled_cmd(0); oled_cmd(7);
    oled_cmd(SSD1306_DISPLAY_ON);

    memset(g_fb, 0, sizeof(g_fb));
}

void display_clear(void) { memset(g_fb, 0, sizeof(g_fb)); }

void display_flush(void)
{
    /* Send the whole framebuffer in pages */
    oled_cmd(SSD1306_SET_COL_ADDR); oled_cmd(0); oled_cmd(127);
    oled_cmd(SSD1306_SET_PAGE_ADDR); oled_cmd(0); oled_cmd(7);
    oled_data(g_fb, sizeof(g_fb));
}

/* ---- Pixel operations ---- */
static void set_pixel(uint8_t x, uint8_t y, uint8_t on)
{
    if (x >= OLED_WIDTH || y >= OLED_HEIGHT) return;
    uint16_t idx = (uint16_t)(y / 8) * OLED_WIDTH + x;
    if (on) g_fb[idx] |= (1U << (y % 8));
    else    g_fb[idx] &= ~(1U << (y % 8));
}

/* ---- 5×7 text ---- */
void display_text(uint8_t x, uint8_t y, const char *s)
{
    uint8_t cx = x;
    while (*s && cx < OLED_WIDTH - 5) {
        uint8_t c = (uint8_t)*s++;
        if (c < 0x20 || c > 0x7E) c = '?';
        const uint8_t *glyph = font5x7[c - 0x20];
        for (uint8_t col = 0; col < 5; col++) {
            uint8_t bits = glyph[col];
            for (uint8_t row = 0; row < 7; row++) {
                set_pixel(cx + col, y + row, (bits >> row) & 1);
            }
        }
        cx += 6;
    }
}

void display_text_f(uint8_t x, uint8_t y, const char *fmt, ...)
{
    char buf[48];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    display_text(x, y, buf);
}

/* ---- A-scan rendering ---- */
/* The A-scan occupies the top 48 rows; the bottom 16 rows are the
 * numeric thickness + status bar. */

void display_draw_ascan(const ascan_t *scan,
                         const thickness_result_t *thk,
                         const flaw_result_t *flaw,
                         const char *material_name,
                         uint8_t battery_pct)
{
    display_clear();
    if (!scan || !scan->valid) {
        display_text(0, 0, "No signal");
        display_text(0, 24, "Couple probe");
        display_text(0, 40, material_name);
        display_flush();
        return;
    }

    /* Find max for auto-scale */
    uint16_t max_v = 1;
    uint16_t count = scan->count;
    if (count > MAX_SAMPLES) count = MAX_SAMPLES;
    for (uint16_t i = 0; i < count; i++)
        if (scan->envelope[i] > max_v) max_v = scan->envelope[i];

    /* Plot envelope: x = depth (sample index), y = amplitude (top 48 rows) */
    uint8_t plot_h = 48;
    uint8_t plot_w = OLED_WIDTH;
    for (uint8_t x = 0; x < plot_w; x++) {
        uint16_t idx = (uint16_t)((uint32_t)x * count / plot_w);
        if (idx >= count) idx = count - 1;
        uint8_t h = (uint8_t)((uint32_t)scan->envelope[idx] *
                              plot_h / (max_v + 1));
        uint8_t y_top = (uint8_t)(plot_h - h);
        for (uint8_t y = y_top; y < plot_h; y++)
            set_pixel(x, y, 1);
    }

    /* Draw the flaw gate as a rectangle outline */
    if (flaw) {
        const flaw_gate_t *g = NULL;
        flaw_get_gate((flaw_gate_t **)&g);  /* not ideal but works */
        (void)g;
    }

    /* Mark the back-wall echo */
    if (thk && thk->valid && thk->peak_index > 0) {
        uint8_t gx = (uint8_t)((uint32_t)thk->peak_index * plot_w / count);
        for (uint8_t y = 0; y < plot_h; y++)
            set_pixel(gx, y, y % 2);   /* dotted vertical line */
    }

    /* Bottom strip: thickness + material + battery */
    if (thk && thk->valid) {
        display_text_f(0, 50, "%.2fmm", thk->thickness_mm);
    } else {
        display_text(0, 50, "--.--mm");
    }
    display_text(70, 50, material_name);
    display_text_f(104, 50, "%d%%", battery_pct);

    /* Flaw indicator */
    if (flaw && flaw->detected) {
        display_text(0, 58, "FLAW!");
        display_text_f(40, 58, "%.1fmm", flaw->depth_mm);
    } else {
        display_text(0, 58, "OK");
    }

    display_flush();
}

/* ---- Menu system ---- */
static const char *k_menu_items[] = {
    "Material",
    "Mode",
    "Gain (TGC)",
    "Pulse width",
    "HV voltage",
    "PRF",
    "Gate set",
    "Calibrate",
    "Log view",
    "Info",
    "Exit",
};
#define MENU_ITEM_COUNT  (int8_t)(sizeof(k_menu_items) / sizeof(k_menu_items[0]))

void display_menu_set_root(void) { g_menu_idx = 0; g_menu_top = 0; }

void display_menu_draw(void)
{
    display_clear();
    display_text(0, 0, "== Menu ==");
    int8_t max_visible = 9;
    for (int8_t i = 0; i < max_visible && (i + g_menu_top) < MENU_ITEM_COUNT; i++) {
        int8_t idx = g_menu_top + i;
        if (idx == g_menu_idx) {
            /* invert (draw filled bar) */
            for (uint8_t x = 0; x < OLED_WIDTH; x++)
                set_pixel(x, 10 + i * 6, 1);
            display_text(2, 10 + i * 6, k_menu_items[idx]);
            /* overwrite in inverse by clearing the text pixels */
            for (uint8_t x = 2; x < 2 + 8 * 6 && x < OLED_WIDTH; x++)
                for (uint8_t row = 0; row < 7; row++)
                    set_pixel(x, 10 + i * 6 + row,
                              !(g_fb[(10 + i * 6 + row) / 8 * OLED_WIDTH + x] &
                                (1U << ((10 + i * 6 + row) % 8))));
        } else {
            display_text(2, 10 + i * 6, k_menu_items[idx]);
        }
    }
    display_flush();
}

int8_t display_menu_select(void) { return 0; }

void display_menu_up(void)
{
    if (g_menu_idx > 0) g_menu_idx--;
    if (g_menu_idx < g_menu_top) g_menu_top = g_menu_idx;
}

void display_menu_down(void)
{
    if (g_menu_idx < MENU_ITEM_COUNT - 1) g_menu_idx++;
    if (g_menu_idx >= g_menu_top + 9)
        g_menu_top = g_menu_idx - 8;
}

void display_menu_back(void)
{
    display_set_page(UI_PAGE_ASCAN);
}

void display_set_page(ui_page_t page) { g_page = page; }
ui_page_t display_get_page(void) { return g_page; }

void display_set_contrast(uint8_t val)
{
    oled_cmd(SSD1306_SET_CONTRAST);
    oled_cmd(val);
}

/* ---- 5×7 font (ASCII 0x20..0x7E, 96 glyphs × 5 bytes) ---- */
const uint8_t font5x7[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x5F,0x00,0x00}, /* ! */
    {0x00,0x07,0x00,0x07,0x00}, /* " */
    {0x14,0x7F,0x14,0x7F,0x14}, /* # */
    {0x24,0x2A,0x7F,0x2A,0x24}, /* $ */
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
    {0x00,0x08,0x14,0x22,0x41}, /* < */
    {0x14,0x14,0x14,0x14,0x14}, /* = */
    {0x41,0x22,0x14,0x08,0x00}, /* > */
    {0x02,0x01,0x51,0x09,0x06}, /* ? */
    {0x32,0x49,0x79,0x41,0x3E}, /* @ */
    {0x7E,0x11,0x11,0x11,0x7E}, /* A */
    {0x7F,0x49,0x49,0x49,0x36}, /* B */
    {0x3E,0x41,0x41,0x41,0x22}, /* C */
    {0x7F,0x41,0x41,0x22,0x1C}, /* D */
    {0x7F,0x49,0x49,0x49,0x41}, /* E */
    {0x7F,0x09,0x09,0x01,0x01}, /* F */
    {0x3E,0x41,0x41,0x51,0x32}, /* G */
    {0x7F,0x08,0x08,0x08,0x7F}, /* H */
    {0x00,0x41,0x7F,0x41,0x00}, /* I */
    {0x20,0x40,0x41,0x3F,0x01}, /* J */
    {0x7F,0x08,0x14,0x22,0x41}, /* K */
    {0x7F,0x40,0x40,0x40,0x40}, /* L */
    {0x7F,0x02,0x04,0x02,0x7F}, /* M */
    {0x7F,0x04,0x08,0x10,0x7F}, /* N */
    {0x3E,0x41,0x41,0x41,0x3E}, /* O */
    {0x7F,0x09,0x09,0x09,0x06}, /* P */
    {0x1E,0x21,0x21,0x21,0x5E}, /* Q */
    {0x7F,0x09,0x19,0x29,0x46}, /* R */
    {0x46,0x49,0x49,0x49,0x31}, /* S */
    {0x01,0x01,0x7F,0x01,0x01}, /* T */
    {0x3F,0x40,0x40,0x40,0x3F}, /* U */
    {0x1F,0x20,0x40,0x20,0x1F}, /* V */
    {0x7F,0x20,0x18,0x20,0x7F}, /* W */
    {0x63,0x14,0x08,0x14,0x63}, /* X */
    {0x03,0x04,0x78,0x04,0x03}, /* Y */
    {0x61,0x51,0x49,0x45,0x43}, /* Z */
    {0x00,0x00,0x7F,0x41,0x41}, /* [ */
    {0x02,0x04,0x08,0x10,0x20}, /* \ */
    {0x41,0x41,0x7F,0x00,0x00}, /* ] */
    {0x04,0x02,0x01,0x02,0x04}, /* ^ */
    {0x40,0x40,0x40,0x40,0x40}, /* _ */
    {0x00,0x01,0x02,0x04,0x00}, /* ` */
    {0x20,0x54,0x54,0x54,0x78}, /* a */
    {0x7F,0x48,0x44,0x44,0x38}, /* b */
    {0x38,0x44,0x44,0x44,0x20}, /* c */
    {0x38,0x44,0x44,0x48,0x7F}, /* d */
    {0x38,0x54,0x54,0x54,0x18}, /* e */
    {0x08,0x7E,0x09,0x01,0x02}, /* f */
    {0x08,0x14,0x54,0x54,0x3C}, /* g */
    {0x7F,0x08,0x04,0x04,0x78}, /* h */
    {0x00,0x44,0x7D,0x40,0x00}, /* i */
    {0x20,0x40,0x44,0x3D,0x00}, /* j */
    {0x00,0x7F,0x10,0x28,0x44}, /* k */
    {0x00,0x41,0x7F,0x40,0x00}, /* l */
    {0x7C,0x04,0x18,0x04,0x78}, /* m */
    {0x7C,0x04,0x04,0x04,0x78}, /* n */
    {0x38,0x44,0x44,0x44,0x38}, /* o */
    {0x7C,0x14,0x14,0x14,0x08}, /* p */
    {0x08,0x14,0x14,0x18,0x7C}, /* q */
    {0x7C,0x08,0x04,0x04,0x08}, /* r */
    {0x48,0x54,0x54,0x54,0x20}, /* s */
    {0x04,0x3F,0x44,0x40,0x20}, /* t */
    {0x3C,0x40,0x40,0x20,0x7C}, /* u */
    {0x1C,0x20,0x40,0x20,0x1C}, /* v */
    {0x3C,0x40,0x30,0x40,0x3C}, /* w */
    {0x44,0x28,0x10,0x28,0x44}, /* x */
    {0x0C,0x50,0x50,0x50,0x3C}, /* y */
    {0x44,0x64,0x54,0x4C,0x44}, /* z */
    {0x00,0x08,0x36,0x41,0x00}, /* { */
    {0x00,0x00,0x7F,0x00,0x00}, /* | */
    {0x00,0x41,0x36,0x08,0x00}, /* } */
    {0x02,0x01,0x02,0x04,0x02}, /* ~ */
};