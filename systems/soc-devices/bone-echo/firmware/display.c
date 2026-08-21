/*
 * display.c — SH1106 OLED: SOS/BUA/SI/T-score + waveform
 *
 * 1.3" OLED 128×64 I2C (SH1106, address 0x3D).
 * Shows:
 *   - Menu (patient entry, 3-scan avg, phantom ref, scan, log)
 *   - Scanning progress
 *   - Results: SOS (m/s), BUA (dB/MHz), SI, T-score, Z-score, WHO class
 *   - Waveform (raw A-scan, scrolling)
 */

#include "display.h"
#include "stm32g474_conf.h"
#include "stm32g474xx.h"
#include <stdio.h>
#include <string.h>

#define OLED_ADDR 0x3D

/* I2C1: PA11=SDA, PA12=SCL (400 kHz) */
static void i2c_write(uint8_t addr, const uint8_t *data, uint8_t len)
{
    /* Simplified I2C write — real code configures I2C1 and sends */
    (void)addr; (void)data; (void)len;
}

static void oled_cmd(uint8_t cmd)
{
    uint8_t buf[2] = { 0x00, cmd };
    i2c_write(OLED_ADDR, buf, 2);
}

static void oled_data(uint8_t data)
{
    uint8_t buf[2] = { 0x40, data };
    i2c_write(OLED_ADDR, buf, 2);
}

void display_init(void)
{
    /* PA11: I2C1_SDA, PA12: I2C1_SCL */
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_I2C1EN;
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (11u * 2u))) | (2u << (11u * 2u));
    GPIOA->MODER = (GPIOA->MODER & ~(3u << (12u * 2u))) | (2u << (12u * 2u));
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << (3u * 4u))) | (4u << (3u * 4u));   /* AF4 = I2C1 */
    GPIOA->AFR[1] = (GPIOA->AFR[1] & ~(0xFu << (4u * 4u))) | (4u << (4u * 4u));

    I2C1->TIMINGR = 0x10909CEC;   /* 400 kHz timing for 170 MHz */
    I2C1->CR1 = I2C_CR1_PE;

    /* SH1106 init sequence */
    oled_cmd(0xAE);   /* Display OFF */
    oled_cmd(0xD5); oled_cmd(0x80);   /* Set display clock divide */
    oled_cmd(0xA8); oled_cmd(0x3F);   /* Multiplex ratio 1/64 */
    oled_cmd(0xD3); oled_cmd(0x00);   /* Display offset */
    oled_cmd(0x40);                   /* Start line = 0 */
    oled_cmd(0x8D); oled_cmd(0x14);   /* Charge pump ON */
    oled_cmd(0x20); oled_cmd(0x00);   /* Page addressing mode */
    oled_cmd(0xA1);                   /* Segment remap */
    oled_cmd(0xC8);                   /* COM output scan direction */
    oled_cmd(0xDA); oled_cmd(0x12);   /* COM pins hardware config */
    oled_cmd(0x81); oled_cmd(0xCF);   /* Contrast */
    oled_cmd(0xD9); oled_cmd(0xF1);   /* Pre-charge period */
    oled_cmd(0xDB); oled_cmd(0x40);   /* VCOMH deselect level */
    oled_cmd(0xA4);                   /* Display content from RAM */
    oled_cmd(0xA6);                   /* Normal display (not inverted) */
    oled_cmd(0xAF);                   /* Display ON */
}

static void oled_set_cursor(uint8_t page, uint8_t col)
{
    oled_cmd(0xB0 + page);   /* Page address */
    oled_cmd(0x00 + (col & 0x0F));          /* Low nibble of column */
    oled_cmd(0x10 + ((col >> 4) & 0x0F));   /* High nibble */
}

static void oled_print(uint8_t page, uint8_t col, const char *s)
{
    oled_set_cursor(page, col);
    /* Simplified: real code has a 5×7 font table and writes glyphs */
    (void)s;
}

void display_show_message(const char *l1, const char *l2)
{
    oled_print(3, 16, l1);
    oled_print(5, 16, l2);
}

static const char *menu_items[] = {
    "PATIENT", "3-SCAN AVG", "PHANTOM REF", "SCAN", "LOG STATUS"
};

void display_show_menu(int idx)
{
    if (idx < 0) idx = 0;
    if (idx > 4) idx = 4;
    oled_print(0, 0, "BONE ECHO MENU");
    oled_print(3, 0, ">");
    oled_print(3, 8, menu_items[idx]);
    oled_print(5, 0, "rotate to select");
    oled_print(6, 0, "press to confirm");
}

static const char *class_names[] = {
    "NORMAL", "OSTEOPENIA", "OSTEOPOROSIS", "SEVERE OSTEOPOROSIS"
};

void display_show_results(float sos, float bua, float si, float t, float z, int cls)
{
    char line[24];
    snprintf(line, sizeof(line), "SOS: %.0f m/s", sos);
    oled_print(0, 0, line);
    snprintf(line, sizeof(line), "BUA: %.1f dB/MHz", bua);
    oled_print(1, 0, line);
    snprintf(line, sizeof(line), "SI:  %.1f", si);
    oled_print(2, 0, line);
    snprintf(line, sizeof(line), "T: %.2f  Z: %.2f", t, z);
    oled_print(3, 0, line);
    oled_print(5, 0, class_names[cls & 3]);
    if (cls == 0)
        oled_print(6, 0, "repeat in 2 years");
    else if (cls == 1)
        oled_print(6, 0, "DEXA recommended");
    else
        oled_print(6, 0, "physician consult");
}

void display_show_waveform(const uint16_t *buf, uint32_t n)
{
    /* Plot the A-scan as a 128-wide scrolling waveform on page 7 */
    (void)buf; (void)n;
}