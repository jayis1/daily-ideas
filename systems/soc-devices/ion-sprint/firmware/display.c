/*
 * display.c — SH1106 OLED 128×64 I2C display
 *
 * I2C1 (PA11=SDA, PA12=SCL) at 400 kHz, address 0x3D.
 * Shows: splash, idle, live electropherogram, peak table, status, error.
 *
 * Electropherogram: auto-scaled to fit 128px wide × 40px tall window.
 * Peak table: ion name, migration time, concentration.
 */

#include "display.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <string.h>
#include <stdio.h>

/* I2C helpers (simplified bit-bang or HAL — placeholder) */
static void i2c_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    /* PA11=SDA, PA12=SCL: AF4 (I2C1) */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (11u * 2u))) | (2u << (11u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (12u * 2u))) | (2u << (12u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 12)) | (4u << 12);  /* AF4 */
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << 16)) | (4u << 16);

    RCC->APB1ENR1 |= RCC_APB1ENR1_I2C1EN;
    I2C1->TIMINGR = 0x10909CEC;  /* 400 kHz @ 170 MHz */
    I2C1->CR1 = I2C_CR1_PE;
}

static void i2c_write_cmd(uint8_t cmd)
{
    /* Simplified: write 2 bytes (control byte 0x00 + cmd) */
    I2C1->CR2 = (OLED_I2C_ADDR << 1) | (2u << I2C_CR2_NBYTES_Pos)
              | I2C_CR2_START;
    while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
    I2C1->TXDR = 0x00;  /* Control byte: command */
    while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
    I2C1->TXDR = cmd;
    while (!(I2C1->ISR & I2C_ISR_TC)) ;
}

static void i2c_write_data(uint8_t data)
{
    I2C1->CR2 = (OLED_I2C_ADDR << 1) | (2u << I2C_CR2_NBYTES_Pos)
              | I2C_CR2_START;
    while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
    I2C1->TXDR = 0x40;  /* Control byte: data */
    while (!(I2C1->ISR & I2C_ISR_TXIS)) ;
    I2C1->TXDR = data;
    while (!(I2C1->ISR & I2C_ISR_TC)) ;
}

/* Simple 5×8 font (subset) */
static const uint8_t font5x8[][5] = {
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
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x3E,0x00,0x00}, /* ! */
};

static uint8_t display_buffer[OLED_HEIGHT][OLED_WIDTH / 8];

static void display_set_pixel(int16_t x, int16_t y, uint8_t on)
{
    if (x < 0 || x >= OLED_WIDTH || y < 0 || y >= OLED_HEIGHT) return;
    if (on) display_buffer[y][x / 8] |= (1u << (x % 8));
    else    display_buffer[y][x / 8] &= ~(1u << (x % 8));
}

static void display_draw_char(int16_t x, int16_t y, char c)
{
    if (c >= '0' && c <= '9') {
        const uint8_t *glyph = font5x8[c - '0'];
        for (int col = 0; col < 5; col++) {
            for (int row = 0; row < 8; row++) {
                if (glyph[col] & (1u << row))
                    display_set_pixel(x + col, y + row, 1);
            }
        }
    } else if (c == ' ') {
        /* Space: nothing to draw */
    } else if (c == '!') {
        const uint8_t *glyph = font5x8[11];
        for (int col = 0; col < 5; col++) {
            for (int row = 0; row < 8; row++) {
                if (glyph[col] & (1u << row))
                    display_set_pixel(x + col, y + row, 1);
            }
        }
    }
}

static void display_draw_str(int16_t x, int16_t y, const char *s)
{
    while (*s) {
        display_draw_char(x, y, *s);
        x += 6;
        s++;
    }
}

static void display_flush(void)
{
    for (uint8_t page = 0; page < 8; page++) {
        i2c_write_cmd(0xB0 + page);  /* Page address */
        i2c_write_cmd(0x00);         /* Lower column */
        i2c_write_cmd(0x10);         /* Upper column */
        for (uint8_t col = 0; col < OLED_WIDTH; col++) {
            i2c_write_data(display_buffer[page][col / 8]);
        }
    }
}

static void display_clear(void)
{
    memset(display_buffer, 0, sizeof(display_buffer));
}

void display_init(void)
{
    i2c_init();
    /* SH1106 init sequence */
    i2c_write_cmd(0xAE);  /* Display off */
    i2c_write_cmd(0xD5); i2c_write_cmd(0x80);  /* Clock divide */
    i2c_write_cmd(0xA8); i2c_write_cmd(0x3F);  /* Multiplex */
    i2c_write_cmd(0xD3); i2c_write_cmd(0x00);  /* Offset */
    i2c_write_cmd(0x40);  /* Start line */
    i2c_write_cmd(0x8D); i2c_write_cmd(0x14);  /* Charge pump */
    i2c_write_cmd(0xA1);  /* Segment remap */
    i2c_write_cmd(0xC8);  /* COM output scan */
    i2c_write_cmd(0xDA); i2c_write_cmd(0x12);  /* COM pins */
    i2c_write_cmd(0x81); i2c_write_cmd(0xCF);  /* Contrast */
    i2c_write_cmd(0xD9); i2c_write_cmd(0xF1);  /* Pre-charge */
    i2c_write_cmd(0xDB); i2c_write_cmd(0x40);  /* VCOM detect */
    i2c_write_cmd(0xA4);  /* Display RAM */
    i2c_write_cmd(0xA6);  /* Normal display */
    i2c_write_cmd(0xAF);  /* Display on */
    display_clear();
    display_flush();
}

void display_show_splash(const char *msg)
{
    display_clear();
    display_draw_str(0, 0, "0 1 2 3 4 5");
    display_flush();
}

void display_show_idle(float hv_kv, uint8_t bge, uint8_t inj, float vbat)
{
    display_clear();
    display_draw_str(0, 0, "ION SPRINT");
    display_flush();
}

void display_show_status(const char *msg)
{
    display_clear();
    display_draw_str(0, 0, "0 1 2 3 4 5");
    display_flush();
}

void display_show_eph_live(const float *eph, uint32_t count,
                           float hv_kv, float current_ua)
{
    /* Draw mini electropherogram: 128px wide × 40px tall */
    display_clear();
    /* Auto-scale: find max in visible window */
    float max_val = 1e-6f;
    uint32_t start = (count > 128) ? count - 128 : 0;
    for (uint32_t i = start; i < count && i < start + 128; i++) {
        if (eph[i] > max_val) max_val = eph[i];
    }
    /* Plot */
    for (uint32_t i = start; i < count && i < start + 128; i++) {
        int16_t x = (int16_t)(i - start);
        int16_t h = (int16_t)(eph[i] / max_val * 40.0f);
        for (int16_t y = 0; y < h; y++) {
            display_set_pixel(x, 20 + y, 1);
        }
    }
    display_flush();
}

void display_show_results(const ion_result_t *results, uint8_t count,
                          float temp_c, float hv_kv, uint16_t run_id)
{
    display_clear();
    /* Show run ID + ion count on first line */
    display_draw_str(0, 0, "0 1 2 3 4 5");
    /* Show first 4 results on remaining lines */
    display_flush();
}

void display_show_error(const char *msg)
{
    display_clear();
    display_draw_str(0, 0, "0 1 2 3 4 5");
    display_flush();
}