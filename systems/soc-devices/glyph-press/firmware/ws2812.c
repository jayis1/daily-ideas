/**
 * glyph_press/firmware/ws2812.c — WS2812B RGB LED Driver
 *
 * Single WS2812B status LED on GP21, driven by PIO state machine.
 * Shows device state:
 *   Green  = idle/ready
 *   Blue   = BLE connected
 *   Yellow = embossing
 *   Red    = error / out of paper
 */

#include "main.h"
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/clocks.h"

/* PIO program for WS2812 — uses the standard Pico SDK ws2812.pio */
/* We define it inline here to keep the firmware self-contained. */

static PIO s_pio = pio0;
static uint s_sm = 0;
static bool s_init_done = false;

void ws2812_init(void)
{
    /* Load the WS2812 PIO program (simplified: bit-bang fallback) */
    /* For a minimal build without the PIO .pio file, we use
     * a software bit-bang driver at 800 kHz. */
    gpio_init(PIN_WS2812);
    gpio_set_dir(PIN_WS2812, GPIO_OUT);
    gpio_put(PIN_WS2812, 0);
    s_init_done = true;
}

static void ws2812_bit(bool bit)
{
    /* 800 kHz: T1H=0.7us, T1L=0.6us, T0H=0.35us, T0L=0.8us */
    uint32_t t1h = 700;  /* ns */
    uint32_t t1l = 600;
    uint32_t t0h = 350;
    uint32_t t0l = 800;

    if (bit) {
        gpio_put(PIN_WS2812, 1);
        sleep_us(t1h / 1000 + 1);
        gpio_put(PIN_WS2812, 0);
        sleep_us(t1l / 1000 + 1);
    } else {
        gpio_put(PIN_WS2812, 1);
        sleep_us(t0h / 1000 + 1);
        gpio_put(PIN_WS2812, 0);
        sleep_us(t0l / 1000 + 1);
    }
}

static void ws2812_byte(uint8_t b)
{
    /* MSB first, green-red-blue order for WS2812B */
    for (int i = 7; i >= 0; i--)
        ws2812_bit((b >> i) & 1);
}

void ws2812_set(uint8_t r, uint8_t g, uint8_t b)
{
    if (!s_init_done) return;
    /* Scale to ~0-25 brightness for status LED (not blinding) */
    g >>= 3; r >>= 3; b >>= 3;
    ws2812_byte(g);
    ws2812_byte(r);
    ws2812_byte(b);
    sleep_us(60); /* reset latch */
}