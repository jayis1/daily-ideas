/* oled.c — SH1106 128x64 OLED driver over I2C3.
 * Minimal text-only rendering of the live dashboard.
 */
#include "stm32l4xx_hal.h"
#include "config.h"
#include "oled.h"
#include "dewpoint.h"
#include <stdio.h>
#include <string.h>

extern I2C_HandleTypeDef hi2c3;

static uint8_t oled_buf[1024];  /* 128x64 / 8 */

static void oled_cmd(uint8_t c)
{
    uint8_t buf[2] = { 0x00, c };
    HAL_I2C_Master_Transmit(&hi2c3, OLED_I2C_ADDR, buf, 2, I2C3_TIMEOUT_MS);
}

static void oled_data(uint8_t d)
{
    uint8_t buf[2] = { 0x40, d };
    HAL_I2C_Master_Transmit(&hi2c3, OLED_I2C_ADDR, buf, 2, I2C3_TIMEOUT_MS);
}

void oled_init(void)
{
    HAL_Delay(100);
    oled_cmd(0xAE);  /* display off */
    oled_cmd(0xD5); oled_cmd(0x80);  /* clock divide */
    oled_cmd(0xA8); oled_cmd(0x3F);  /* multiplex 1/64 */
    oled_cmd(0xD3); oled_cmd(0x00);  /* display offset */
    oled_cmd(0x40);                  /* start line 0 */
    oled_cmd(0x8D); oled_cmd(0x14);  /* charge pump */
    oled_cmd(0x20); oled_cmd(0x00);  /* page addressing */
    oled_cmd(0xA1);                  /* segment remap */
    oled_cmd(0xC8);                  /* COM scan dir */
    oled_cmd(0xDA); oled_cmd(0x12);  /* COM pins */
    oled_cmd(0x81); oled_cmd(0xCF);  /* contrast */
    oled_cmd(0xD9); oled_cmd(0xF1);  /* precharge */
    oled_cmd(0xDB); oled_cmd(0x40);  /* VCOMH */
    oled_cmd(0xA4);  /* display RAM */
    oled_cmd(0xA6);  /* normal display */
    oled_cmd(0xAF);  /* display on */
}

/* 5x7 font: each char is 5 columns + 1 blank. Only a subset of ASCII
 * is included here to keep the file short. */
static const uint8_t font5x7[][5] = {
    /* space */ {0x00,0x00,0x00,0x00,0x00},
    /* ! */     {0x00,0x00,0x5F,0x00,0x00},
    /* 0..9 */  {0x3E,0x51,0x49,0x45,0x3E}, /* 0 */
                {0x00,0x42,0x7F,0x40,0x00}, /* 1 */
                {0x42,0x61,0x51,0x49,0x46}, /* 2 */
                {0x21,0x41,0x45,0x4B,0x31}, /* 3 */
                {0x18,0x14,0x12,0x7F,0x10}, /* 4 */
                {0x27,0x45,0x45,0x45,0x39}, /* 5 */
                {0x3C,0x4A,0x49,0x49,0x30}, /* 6 */
                {0x01,0x71,0x09,0x05,0x03}, /* 7 */
                {0x36,0x49,0x49,0x49,0x36}, /* 8 */
                {0x06,0x49,0x49,0x29,0x1E}, /* 9 */
};

static void oled_text(int row, int col, const char *s)
{
    /* row = page (0..7), col = 0..127 */
    oled_cmd(0xB0 + (row & 0x07));
    oled_cmd(0x00 + (col & 0x0F));
    oled_cmd(0x10 + ((col >> 4) & 0x0F));
    while (*s) {
        char c = *s++;
        const uint8_t *g;
        if (c == ' ')      g = font5x7[0];
        else if (c == '!')  g = font5x7[1];
        else if (c >= '0' && c <= '9') g = font5x7[2 + (c - '0')];
        else {
            /* unknown chars → space */
            g = font5x7[0];
        }
        for (int i = 0; i < 5; i++) oled_data(g[i]);
        oled_data(0x00);
    }
}

void oled_update(const humidity_t *h, float mirror_c, float t_air,
                 float tec_i, int state, const char *state_str)
{
    char line[24];
    snprintf(line, sizeof(line), "Dew  %.2f C", h->dew_c);
    oled_text(0, 0, line);
    snprintf(line, sizeof(line), "RH   %.1f %%", h->rh_pct);
    oled_text(1, 0, line);
    snprintf(line, sizeof(line), "AH   %.1f g/m3", h->ah_gm3);
    oled_text(2, 0, line);
    snprintf(line, sizeof(line), "Mir  %.2f C", mirror_c);
    oled_text(3, 0, line);
    snprintf(line, sizeof(line), "Air  %.2f C", t_air);
    oled_text(4, 0, line);
    snprintf(line, sizeof(line), "TEC  %.2f A", tec_i);
    oled_text(5, 0, line);
    snprintf(line, sizeof(line), "Pha  %s", h->phase ? "FROST" : "DEW");
    oled_text(6, 0, line);
    oled_text(7, 0, state_str);
}