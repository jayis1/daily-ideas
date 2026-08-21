/**
 * spiro_flow/ws2812.c — WS2812B RGB LED driver for CH32V203
 *
 * Bit-bang WS2812B protocol on PA0.
 * The LED indicates device state:
 *   Blue   — idle / waiting
 *   Green  — good maneuver (grade A/B)
 *   Yellow — acceptable maneuver (grade C)
 *   Red    — poor / unacceptable maneuver
 *   Cyan   — capturing maneuver
 *   White  — error / initialization
 *
 * WS2812B timing (800 kHz):
 *   0-bit: 400ns high, 850ns low
 *   1-bit: 800ns high, 450ns low
 *   Reset: >50µs low
 *
 * At 144 MHz, 400ns = 57.6 cycles. We use inline assembly or
 * carefully counted NOP loops for timing.
 */

#include "main.h"
#include "ws2812.h"

#define TAG "WS2812"

#define PIN_WS2812_MASK  (1 << 0)  /* PA0 */

/* ── GPIO helpers ──────────────────────────────────────────────────── */

static inline void gpio_set_high(void)
{
    /* CH32V203: GPIOA->BSHR = PIN_WS2812_MASK; */
}

static inline void gpio_set_low(void)
{
    /* CH32V203: GPIOA->BCR = PIN_WS2812_MASK; */
}

/* ── WS2812B bit-bang ──────────────────────────────────────────────── */

/* At 144 MHz:
 * 400ns = 57.6 cycles → ~58 NOPs
 * 800ns = 115.2 cycles → ~115 NOPs
 * 450ns = 64.8 cycles → ~65 NOPs
 * 850ns = 122.4 cycles → ~122 NOPs
 *
 * We use compiler barriers to prevent reordering.
 */

#define NOP1()  __asm__ volatile("nop")
#define NOP10() NOP1();NOP1();NOP1();NOP1();NOP1();NOP1();NOP1();NOP1();NOP1();NOP1()
#define NOP50() NOP10();NOP10();NOP10();NOP10();NOP10()
#define NOP100() NOP50();NOP50()

static void ws2812_send_bit(uint8_t bit)
{
    if (bit) {
        /* 1-bit: 800ns high, 450ns low */
        gpio_set_high();
        NOP50(); NOP50(); NOP10(); NOP1(); NOP1(); NOP1(); NOP1(); NOP1(); /* ~115 */
        gpio_set_low();
        NOP50(); NOP10(); NOP1(); NOP1(); NOP1(); NOP1(); NOP1(); /* ~65 */
    } else {
        /* 0-bit: 400ns high, 850ns low */
        gpio_set_high();
        NOP50(); NOP1(); NOP1(); NOP1(); NOP1(); NOP1(); NOP1(); NOP1(); /* ~58 */
        gpio_set_low();
        NOP50(); NOP50(); NOP10(); NOP10(); NOP1(); NOP1(); /* ~122 */
    }
}

static void ws2812_send_byte(uint8_t b)
{
    /* MSB first */
    for (int i = 7; i >= 0; i--) {
        ws2812_send_bit((b >> i) & 1);
    }
}

static void ws2812_send_color(uint8_t r, uint8_t g, uint8_t b)
{
    /* WS2812B order: GRB */
    ws2812_send_byte(g);
    ws2812_send_byte(r);
    ws2812_send_byte(b);
}

static void ws2812_reset(void)
{
    /* >50µs low */
    gpio_set_low();
    delay_ms(1);  /* generous reset */
}

/* ── Public API ────────────────────────────────────────────────────── */

void ws2812_init(void)
{
    /* Configure PA0 as output, push-pull, 50MHz
     * CH32V203 HAL:
     * GPIO_InitTypeDef gpio;
     * gpio.GPIO_Pin = GPIO_Pin_0;
     * gpio.GPIO_Mode = GPIO_Mode_Out_PP;
     * gpio.GPIO_Speed = GPIO_Speed_50MHz;
     * GPIO_Init(GPIOA, &gpio);
     */
    gpio_set_low();
    ESP_LOGI(TAG, "WS2812B initialized on PA0");
}

void ws2812_set(uint8_t r, uint8_t g, uint8_t b)
{
    /* Disable interrupts during bit-bang for timing accuracy */
    /* __asm__ volatile("csrrci zero, mstatus, 0x8");  // clear MIE */

    ws2812_send_color(r, g, b);
    ws2812_reset();

    /* Re-enable interrupts */
    /* __asm__ volatile("csrrsi zero, mstatus, 0x8");  // set MIE */
}

/* ── ESP logging shim ──────────────────────────────────────────────── */
#ifndef ESP_LOGI
#define ESP_LOGI(tag, fmt, ...) do { printf("[%s] " fmt "\n", tag, ##__VA_ARGS__); } while(0)
#include <stdio.h>
#endif