/*
 * display.c — SH1106 OLED 128×64 I2C display
 *
 * I2C1 (PA11=SDA, PA12=SCL) at 400 kHz, address 0x3D.
 * Shows: splash, idle/status, live DNI/AOD, Langley progress, menu, error.
 *
 * DNI bar: horizontal bar chart (0–1400 W/m²) across top 16 px.
 * AOD table: 6 wavelength values in 2 columns.
 * Sun position: azimuth/elevation at bottom.
 */

#include "display.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <string.h>
#include <stdio.h>

/* ---- Frame buffer: 128×64 = 1024 bytes, 8 pages of 128 bytes ---- */
static uint8_t fb[1024];
static bool dirty = false;

/* ---- I2C helpers ---- */
static void i2c_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_I2C1EN;
    /* PA11=SDA, PA12=SCL: AF4 */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (11u * 2u))) | (2u << (11u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (12u * 2u))) | (2u << (12u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 12)) | (4u << 12);
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 16)) | (4u << 16);
    I2C1->TIMINGR = 0x10909CEC;  /* 400 kHz @ 170 MHz */
    I2C1->CR1 = I2C_CR1_PE;
}

static void i2c_write_cmd(uint8_t cmd)
{
    I2C1->CR2 = (OLED_I2C_ADDR << 1) | (2u << I2C_CR2_NBYTES_Pos)
              | I2C_CR2_START;
    while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
    I2C1->TXDR = 0x00;
    while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
    I2C1->TXDR = cmd;
    while (!(I2C1->ISR & I2C_ISR_TC)) ;
    I2C1->CR2 = I2C_CR2_STOP;
}

static void i2c_write_data(const uint8_t *data, uint16_t len)
{
    I2C1->CR2 = (OLED_I2C_ADDR << 1) | ((len + 1u) << I2C_CR2_NBYTES_Pos)
              | I2C_CR2_START;
    while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
    I2C1->TXDR = 0x40;   /* Control byte: data */
    for (uint16_t i = 0; i < len; i++) {
        while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
        I2C1->TXDR = data[i];
    }
    while (!(I2C1->ISR & I2C_ISR_TC)) ;
    I2C1->CR2 = I2C_CR2_STOP;
}

/* ---- Frame buffer operations ---- */
static void fb_clear(void)
{
    memset(fb, 0, sizeof(fb));
    dirty = true;
}

static void fb_set_pixel(uint8_t x, uint8_t y, bool on)
{
    if (x >= OLED_WIDTH || y >= OLED_HEIGHT) return;
    uint16_t idx = (y / 8) * OLED_WIDTH + x;
    if (on) fb[idx] |=  (1u << (y % 8));
    else    fb[idx] &= ~(1u << (y % 8));
    dirty = true;
}

/* ---- Minimal 5×7 font (printable ASCII subset) ---- */
static const uint8_t font5x7[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x5F,0x00,0x00}, /* ! */
    /* ... abbreviated font; full font in production */
};

static void fb_draw_char(uint8_t x, uint8_t y, char c)
{
    if (c < ' ' || c > '~') c = '?';
    uint8_t idx = (c - ' ') < 3 ? (c - ' ') : 0;
    const uint8_t *glyph = font5x7[idx];
    for (uint8_t col = 0; col < 5; col++) {
        for (uint8_t row = 0; row < 7; row++) {
            if (glyph[col] & (1u << row))
                fb_set_pixel(x + col, y + row, true);
        }
    }
}

static void fb_draw_str(uint8_t x, uint8_t y, const char *s)
{
    while (*s) {
        fb_draw_char(x, y, *s);
        x += 6;
        s++;
    }
}

static void fb_draw_hline(uint8_t x, uint8_t y, uint8_t w)
{
    for (uint8_t i = 0; i < w; i++) fb_set_pixel(x + i, y, true);
}

static void fb_draw_bar(uint8_t x, uint8_t y, uint8_t w, uint8_t h,
                         float value, float max)
{
    uint8_t fill = (uint8_t)((value / max) * w);
    if (fill > w) fill = w;
    for (uint8_t i = 0; i < w; i++) {
        for (uint8_t j = 0; j < h; j++) {
            fb_set_pixel(x + i, y + j, i < fill);
        }
    }
}

/* ---- Flush frame buffer to OLED ---- */
static void display_flush(void)
{
    if (!dirty) return;
    for (uint8_t page = 0; page < 8; page++) {
        i2c_write_cmd(0xB0 | page);       /* Set page address */
        i2c_write_cmd(0x00 | 2);          /* Lower column = 2 (offset) */
        i2c_write_cmd(0x10);              /* Upper column = 0 */
        i2c_write_data(&fb[page * OLED_WIDTH], OLED_WIDTH);
    }
    dirty = false;
}

/* ---- Public API ---- */

void display_init(void)
{
    i2c_init();
    /* SH1106 initialization sequence */
    i2c_write_cmd(0xAE);   /* Display off */
    i2c_write_cmd(0xD5); i2c_write_cmd(0x50);   /* Set display clock */
    i2c_write_cmd(0xA8); i2c_write_cmd(0x3F);   /* Multiplex ratio */
    i2c_write_cmd(0xD3); i2c_write_cmd(0x00);   /* Display offset */
    i2c_write_cmd(0x40);   /* Set start line */
    i2c_write_cmd(0x8D); i2c_write_cmd(0x14);   /* Charge pump */
    i2c_write_cmd(0x20); i2c_write_cmd(0x00);   /* Memory mode */
    i2c_write_cmd(0xA1);   /* Segment remap */
    i2c_write_cmd(0xC8);   /* COM scan direction */
    i2c_write_cmd(0xDA); i2c_write_cmd(0x12);   /* COM pins */
    i2c_write_cmd(0x81); i2c_write_cmd(0xCF);   /* Contrast */
    i2c_write_cmd(0xD9); i2c_write_cmd(0xF1);   /* Pre-charge */
    i2c_write_cmd(0xDB); i2c_write_cmd(0x40);   /* VCOM detect */
    i2c_write_cmd(0xA4);   /* Display resume */
    i2c_write_cmd(0xA6);   /* Normal display */
    i2c_write_cmd(0xAF);   /* Display on */
    fb_clear();
    display_flush();
}

void display_show_splash(const char *msg)
{
    fb_clear();
    fb_draw_str(0, 0, "HELIO TILT v1.0");
    fb_draw_str(0, 16, "Solar Radiometer");
    if (msg) fb_draw_str(0, 32, msg);
    fb_draw_str(0, 48, "Initializing...");
    display_flush();
}

void display_show_status(float dni, float aod870, float angstrom,
                          float pwv, float sun_az, float sun_el,
                          float bat_v, const char *state_name)
{
    char buf[24];
    fb_clear();
    fb_draw_str(0, 0, "HELIO TILT");
    fb_draw_str(90, 0, state_name);

    snprintf(buf, sizeof(buf), "DNI:%5.0f W/m2", dni);
    fb_draw_str(0, 12, buf);
    snprintf(buf, sizeof(buf), "AOD870:%.3f", aod870);
    fb_draw_str(0, 22, buf);
    snprintf(buf, sizeof(buf), "AE:%.2f PWV:%.1f", angstrom, pwv);
    fb_draw_str(0, 32, buf);
    snprintf(buf, sizeof(buf), "Sun:%3.0f/%2.0f", sun_az, sun_el);
    fb_draw_str(0, 42, buf);
    snprintf(buf, sizeof(buf), "Bat:%.2fV", bat_v);
    fb_draw_str(0, 54, buf);
    display_flush();
}

void display_show_tracking(const radiometry_result_t *result,
                            const solar_pos_t *pos, float bat_v)
{
    char buf[24];
    fb_clear();

    /* DNI bar chart (0–1400 W/m²) across top */
    fb_draw_str(0, 0, "DNI");
    fb_draw_bar(24, 0, 100, 8, result->dni[WL_870], THERMOPILE_DNI_MAX);

    /* AOD table: 6 wavelengths in 2 columns */
    snprintf(buf, sizeof(buf), "405:%.2f 675:%.2f",
             result->aod[WL_405], result->aod[WL_675]);
    fb_draw_str(0, 14, buf);
    snprintf(buf, sizeof(buf), "440:%.2f 870:%.2f",
             result->aod[WL_440], result->aod[WL_870]);
    fb_draw_str(0, 24, buf);
    snprintf(buf, sizeof(buf), "940:%.2f 1640:%.2f",
             result->aod[WL_940], result->aod[WL_1640]);
    fb_draw_str(0, 34, buf);

    /* Ångström + PWV */
    snprintf(buf, sizeof(buf), "a:%.2f PWV:%.1fcm",
             result->angstrom_alpha, result->pwv_cm);
    fb_draw_str(0, 44, buf);

    /* Sun position + battery */
    snprintf(buf, sizeof(buf), "Az:%.0f El:%.0f V:%.1f",
             pos->azimuth, pos->elevation, bat_v);
    fb_draw_str(0, 54, buf);

    display_flush();
}

void display_show_langley(uint16_t points, float r2, float v0_870)
{
    char buf[24];
    fb_clear();
    fb_draw_str(0, 0, "LANGLEY CAL");
    snprintf(buf, sizeof(buf), "Pts: %d/%d", points, LANGLEY_MIN_POINTS);
    fb_draw_str(0, 16, buf);
    snprintf(buf, sizeof(buf), "R2(870): %.4f", r2);
    fb_draw_str(0, 28, buf);
    snprintf(buf, sizeof(buf), "V0(870): %.4f", v0_870);
    fb_draw_str(0, 40, buf);
    fb_draw_str(0, 54, "Keep clear sky...");
    display_flush();
}

void display_show_menu(const char *items[], uint8_t count, uint8_t sel)
{
    fb_clear();
    fb_draw_str(0, 0, "MENU");
    for (uint8_t i = 0; i < count && i < 8; i++) {
        char marker = (i == sel) ? '>' : ' ';
        char buf[24];
        snprintf(buf, sizeof(buf), "%c%s", marker, items[i]);
        fb_draw_str(0, 12 + i * 8, buf);
    }
    display_flush();
}

void display_show_error(const char *msg)
{
    fb_clear();
    fb_draw_str(0, 0, "ERROR:");
    fb_draw_str(0, 16, msg);
    display_flush();
}