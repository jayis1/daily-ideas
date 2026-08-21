/**
 * sh1106.c — SH1106 1.3" OLED driver (128×64, I2C, page-mode)
 *
 * Minimal text-only display driver. Uses a 5×7 font stored in
 * flash. The SH1106 has a 132×64 internal RAM; we write to the
 * 128 visible columns. Page addressing mode (8 rows × 128 cols).
 */

#include "sh1106.h"
#include <string.h>

#define SH1106_ADDR    (0x3C << 1)
#define SH1106_WIDTH   128
#define SH1106_HEIGHT  64

static I2C_HandleTypeDef *s_i2c = NULL;
static uint8_t s_buffer[SH1106_WIDTH * SH1106_HEIGHT / 8];
static uint8_t s_dirty = 0;

/* 5×7 font (ASCII 32–127, partial — sufficient for UI) */
static const uint8_t font5x7[][5] = {
    {0x00,0x00,0x00,0x00,0x00}, /* space */
    {0x00,0x00,0x5F,0x00,0x00}, /* ! */
    /* ... full font table would go here ... */
    {0x3E,0x51,0x49,0x45,0x3E}, /* 0 */
    {0x00,0x42,0x7F,0x40,0x00}, /* 1 */
    {0x42,0x61,0x51,0x49,0x46}, /* 2 */
    {0x21,0x41,0x45,0x4B,0x31}, /* 3 */
    /* (abbreviated for brevity — production firmware includes full ASCII) */
};

static void cmd(uint8_t c)
{
    uint8_t buf[2] = { 0x00, c };
    HAL_I2C_Master_Transmit(s_i2c, SH1106_ADDR, buf, 2, 50);
}

void sh1106_init(I2C_HandleTypeDef *i2c)
{
    s_i2c = i2c;
    HAL_Delay(100);

    cmd(0xAE);  /* display off */
    cmd(0x02);  /* set low column addr */
    cmd(0x10);  /* set high column addr */
    cmd(0x40);  /* set start line */
    cmd(0x81);  /* set contrast */
    cmd(0xCF);
    cmd(0xA1);  /* segment remap */
    cmd(0xA8);  /* multiplex ratio */
    cmd(0x3F);
    cmd(0xC8);  /* COM scan dir */
    cmd(0xD3);  /* display offset */
    cmd(0x00);
    cmd(0xD5);  /* clock divide */
    cmd(0x80);
    cmd(0xD9);  /* pre-charge */
    cmd(0xF1);
    cmd(0xDA);  /* COM pins */
    cmd(0x12);
    cmd(0xDB);  /* VCOM deselect */
    cmd(0x40);
    cmd(0x8D);  /* charge pump */
    cmd(0x14);
    cmd(0xAF);  /* display on */

    sh1106_clear();
    sh1106_flush();
}

void sh1106_clear(void)
{
    memset(s_buffer, 0, sizeof(s_buffer));
    s_dirty = 1;
}

void sh1106_draw_string(uint8_t x, uint8_t y, const char *str, uint8_t size)
{
    uint8_t page = y / 8;
    uint8_t col = x;
    while (*str && col < SH1106_WIDTH - 5) {
        char ch = *str++;
        /* Simplified: use font index for digits and common chars.
         * Full font lookup would map ASCII 32–127. */
        uint8_t idx = 0;
        if (ch >= '0' && ch <= '3') idx = 2 + (ch - '0');
        /* For other chars, use space placeholder in this stub */
        const uint8_t *glyph = font5x7[idx];
        for (int i = 0; i < 5; i++) {
            uint8_t col_addr = col + i;
            if (col_addr >= SH1106_WIDTH) break;
            s_buffer[page * SH1106_WIDTH + col_addr] = glyph[i];
        }
        col += 6 * size;
    }
    s_dirty = 1;
}

void sh1106_flush(void)
{
    if (!s_dirty) return;
    for (uint8_t p = 0; p < 8; p++) {
        cmd(0xB0 + p);           /* page address */
        cmd(0x02);               /* lower column */
        cmd(0x10);               /* upper column */
        uint8_t buf[SH1106_WIDTH + 1];
        buf[0] = 0x40;           /* data mode */
        memcpy(&buf[1], &s_buffer[p * SH1106_WIDTH], SH1106_WIDTH);
        HAL_I2C_Master_Transmit(s_i2c, SH1106_ADDR, buf, SH1106_WIDTH + 1, 100);
    }
    s_dirty = 0;
}