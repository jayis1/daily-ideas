/*
 * hall-puck / firmware / Core / Src / oled_display.c
 * SSD1306 OLED 128x64 display driver (SPI2)
 *
 * MIT License.
 */
#include "oled_display.h"
#include "main.h"
#include <stdio.h>
#include <string.h>

extern SPI_HandleTypeDef hspi2;

/* SSD1306 commands */
#define SSD1306_SET_CONTRAST    0x81
#define SSD1306_DISPLAY_ON      0xAF
#define SSD1306_DISPLAY_OFF     0xAE
#define SSD1306_NORMAL_DISPLAY  0xA6
#define SSD1306_INVERT_DISPLAY  0xA7
#define SSD1306_SET_COL_ADDR    0x21
#define SSD1306_SET_PAGE_ADDR   0x22
#define SSD1306_SET_START_LINE  0x40
#define SSD1306_SET_SEG_REMAP   0xA0
#define SSD1306_SET_COM_SCAN    0xC0
#define SSD1306_SET_COM_PINS    0xDA
#define SSD1306_SET_CHARGE      0x8D
#define SSD1306_SET_VCOMH       0xDB
#define SSD1306_SET_OSC_FREQ    0xD5
#define SSD1306_SET_PRECHARGE   0xD9
#define SSD1306_SET_MULTIPLEX   0xA8

#define OLED_WIDTH   128
#define OLED_HEIGHT  64
#define OLED_PAGES   (OLED_HEIGHT / 8)

static uint8_t display_buffer[OLED_WIDTH * OLED_PAGES];

static void oled_cs_low(void)
{
    GPIOB->BSRR = (1 << OLED_CS_PIN) << 16;
}

static void oled_cs_high(void)
{
    GPIOB->BSRR = (1 << OLED_CS_PIN);
}

static void oled_dc_command(void)
{
    GPIOB->BSRR = (1 << OLED_DC_PIN) << 16;  /* DC low = command */
}

static void oled_dc_data(void)
{
    GPIOB->BSRR = (1 << OLED_DC_PIN);  /* DC high = data */
}

static void oled_write_command(uint8_t cmd)
{
    oled_dc_command();
    oled_cs_low();
    while (!(SPI2->SR & SPI_SR_TXE));
    *(volatile uint8_t *)&SPI2->DR = cmd;
    while (!(SPI2->SR & SPI_SR_RXNE));
    (void)SPI2->DR;
    oled_cs_high();
}

static void oled_write_data(uint8_t data)
{
    oled_dc_data();
    oled_cs_low();
    while (!(SPI2->SR & SPI_SR_TXE));
    *(volatile uint8_t *)&SPI2->DR = data;
    while (!(SPI2->SR & SPI_SR_RXNE));
    (void)SPI2->DR;
    oled_cs_high();
}

static void oled_reset(void)
{
    /* Reset pulse on OLED_RES_PIN (PB10) */
    GPIOB->BSRR = (1 << OLED_DC_PIN + 10) << 16;  /* RES low */
    delay_ms(10);
    GPIOB->BSRR = (1 << (OLED_DC_PIN + 10));       /* RES high */
    delay_ms(10);
}

/* ---- 5x7 font (simplified) ---- */
static const uint8_t font5x7[][5] = {
    /* Space through Z (0x20–0x5A), simplified subset */
    [0] = {0x00,0x00,0x00,0x00,0x00},  /* space */
    /* ... full font omitted for brevity — use lookup in production */
};

static void oled_set_pixel(int x, int y, int on)
{
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;
    int idx = x + (y / 8) * OLED_WIDTH;
    if (on) display_buffer[idx] |= (1 << (y & 7));
    else display_buffer[idx] &= ~(1 << (y & 7));
}

static void oled_draw_char(int x, int y, char c, int size)
{
    /* Simplified: draw character using font (placeholder) */
    /* In production: full 5x7 font bitmap lookup */
}

static void oled_draw_string(int x, int y, const char *str, int size)
{
    int px = x;
    while (*str) {
        oled_draw_char(px, y, *str, size);
        px += 6 * size;
        str++;
    }
}

static void oled_update(void)
{
    /* Set column and page addresses */
    oled_write_command(SSD1306_SET_COL_ADDR);
    oled_write_command(0);
    oled_write_command(OLED_WIDTH - 1);
    oled_write_command(SSD1306_SET_PAGE_ADDR);
    oled_write_command(0);
    oled_write_command(OLED_PAGES - 1);

    /* Write buffer */
    oled_dc_data();
    oled_cs_low();
    for (int i = 0; i < OLED_WIDTH * OLED_PAGES; i++) {
        while (!(SPI2->SR & SPI_SR_TXE));
        *(volatile uint8_t *)&SPI2->DR = display_buffer[i];
        while (!(SPI2->SR & SPI_SR_RXNE));
        (void)SPI2->DR;
    }
    oled_cs_high();
}

/* ---- Public API ---- */
void oled_init(void)
{
    /* Configure CS, DC, RES pins as output */
    GPIOB->MODER &= ~(3 << (OLED_CS_PIN * 2) | 3 << (OLED_DC_PIN * 2));
    GPIOB->MODER |= (1 << (OLED_CS_PIN * 2) | 1 << (OLED_DC_PIN * 2));

    oled_cs_high();

    oled_reset();

    /* SSD1306 initialization sequence */
    oled_write_command(SSD1306_DISPLAY_OFF);
    oled_write_command(SSD1306_SET_MULTIPLEX); oled_write_command(63);
    oled_write_command(SSD1306_SET_OSC_FREQ); oled_write_command(0x80);
    oled_write_command(SSD1306_SET_CHARGE); oled_write_command(0x14);
    oled_write_command(SSD1306_SET_VCOMH); oled_write_command(0x20);
    oled_write_command(SSD1306_SET_SEG_REMAP | 0x01);  /* mirror */
    oled_write_command(SSD1306_SET_COM_SCAN | 0x08);   /* remap */
    oled_write_command(SSD1306_SET_CONTRAST); oled_write_command(0xCF);
    oled_write_command(SSD1306_SET_PRECHARGE); oled_write_command(0xF1);
    oled_write_command(SSD1306_SET_COM_PINS); oled_write_command(0x12);
    oled_write_command(SSD1306_NORMAL_DISPLAY);
    oled_write_command(0x20); oled_write_command(0x00);  /* horizontal addressing */
    oled_write_command(SSD1306_SET_COL_ADDR); oled_write_command(0); oled_write_command(127);
    oled_write_command(SSD1306_SET_PAGE_ADDR); oled_write_command(0); oled_write_command(7);
    oled_write_command(SSD1306_DISPLAY_ON);

    oled_clear();
}

void oled_clear(void)
{
    memset(display_buffer, 0, sizeof(display_buffer));
    oled_update();
}

void oled_show_idle(float temp_c, const meas_params_t *params)
{
    oled_clear();
    oled_draw_string(0, 0, "Hall Puck", 2);
    oled_draw_string(0, 16, "Ready", 1);
    /* Would display: current, thickness, temperature */
    oled_update();
}

void oled_show_contact_check(int contact, bool ok)
{
    oled_clear();
    oled_draw_string(0, 0, "Contact Check", 1);
    char buf[32];
    /* Display contact status */
    oled_update();
}

void oled_show_vdp_progress(float ra, float rb, float rs)
{
    oled_clear();
    oled_draw_string(0, 0, "Van der Pauw", 1);
    /* Display Ra, Rb, Rs */
    oled_update();
}

void oled_show_hall_progress(const char *phase, float voltage_uv, float b_field)
{
    oled_clear();
    oled_draw_string(0, 0, "Hall: ", 1);
    oled_draw_string(40, 0, phase, 1);
    /* Display V_H and B */
    oled_update();
}

void oled_show_result(const meas_result_t *r)
{
    oled_clear();
    oled_draw_string(0, 0, "Result", 1);

    char buf[24];

    /* Carrier type */
    const char *type_str = (r->carrier_type == CARRIER_N_TYPE) ? "n-type" :
                           (r->carrier_type == CARRIER_P_TYPE) ? "p-type" : "???";
    oled_draw_string(0, 8, type_str, 2);

    /* Mobility */
    /* Would format and display: μ, n, R_s, R_H */

    oled_update();
}

void oled_show_menu(int item, const char **items, int n_items)
{
    oled_clear();
    oled_draw_string(0, 0, "Menu", 1);
    /* Display menu items with cursor */
    oled_update();
}