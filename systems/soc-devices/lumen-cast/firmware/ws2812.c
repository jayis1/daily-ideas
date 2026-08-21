/**
 * lumen_cast/firmware/ws2812.c — WS2812B RGB LED driver
 *
 * Bit-bang WS2812B protocol on PB0.
 * Each LED: 24 bits (G7..G0 R7..R0 B7..B0), MSB first.
 * T0H: 350ns  T0L: 800ns  T1H: 700ns  T1L: 600ns  RST: >50µs low
 *
 * Uses a tight assembly loop at 170 MHz for precise timing.
 */

#include "main.h"

#define TAG "WS28"

void ws2812_init(void)
{
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOBEN;
    GPIOB->MODER &= ~(3 << (PIN_WS2812 * 2));
    GPIOB->MODER |= (1 << (PIN_WS2812 * 2));  /* output */
    GPIOB->OTYPER &= ~(1 << PIN_WS2812);
    GPIOB->OSPEEDR |= (3 << (PIN_WS2812 * 2));  /* high speed */
    ws2812_set(0, 0, 0);
}

static inline void delay_ns(uint32_t ns)
{
    /* At 170 MHz, 1 cycle ≈ 5.88ns. So ns/6 cycles approximately. */
    uint32_t cycles = ns / 6;
    for (uint32_t i = 0; i < cycles; i++) {
        __asm volatile ("nop");
    }
}

void ws2812_set(uint8_t r, uint8_t g, uint8_t b)
{
    /* GRB order, MSB first */
    uint8_t grb[3] = { g, r, b };

    /* Disable interrupts for precise timing */
    uint32_t primask = __get_PRIMASK();
    __disable_irq();

    for (int color = 0; color < 3; color++) {
        uint8_t val = grb[color];
        for (int bit = 7; bit >= 0; bit--) {
            if (val & (1 << bit)) {
                /* T1H: 700ns high, T1L: 600ns low */
                GPIOB->ODR |= (1 << PIN_WS2812);
                delay_ns(700);
                GPIOB->ODR &= ~(1 << PIN_WS2812);
                delay_ns(600);
            } else {
                /* T0H: 350ns high, T0L: 800ns low */
                GPIOB->ODR |= (1 << PIN_WS2812);
                delay_ns(350);
                GPIOB->ODR &= ~(1 << PIN_WS2812);
                delay_ns(800);
            }
        }
    }

    /* Restore interrupts */
    __set_PRIMASK(primask);

    /* Reset: >50µs low */
    delay_ns(55000);
}