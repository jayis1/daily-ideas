/**
 * glyph_press/firmware/emboss.c — Solenoid Embossing Driver
 *
 * Drives 16 solenoids via 2× 74HC595 shift registers + 8× DRV8833 dual H-bridges.
 * Each cell fires all relevant dots simultaneously (parallel embossing).
 *
 * Shift register data: 16 bits = 16 solenoid channels.
 *   Bit 0-7:  column A dots 1-8
 *   Bit 8-15: column B dots 1-8
 * For a single cell, only column A is used (bits 0-7).
 *
 * The 74HC595 chain is driven by bit-banging on GP19/20/21.
 * After latching, the DRV8833 enable lines are pulsed for SOLID_DWELL_MS.
 */

#include "main.h"
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include <string.h>

/* Shift register pins — these are shared with encoder/buzzer,
 * but embossing and UI tasks never run simultaneously on Core 1. */

#define SR_DATA   19
#define SR_CLK    20
#define SR_LATCH  21

/* DRV8833 enable line — we use a single GPIO to enable all drivers
 * (wired-OR via diode, or a dedicated enable transistor) */
#define DRV_ENABLE 22  /* Reuse LED_STATUS pin during emboss */

static bool s_init_done = false;

void emboss_init(void)
{
    gpio_init(SR_DATA);
    gpio_set_dir(SR_DATA, GPIO_OUT);
    gpio_init(SR_CLK);
    gpio_set_dir(SR_CLK, GPIO_OUT);
    gpio_init(SR_LATCH);
    gpio_set_dir(SR_LATCH, GPIO_OUT);

    /* DRV8833 enable (active high) */
    gpio_init(DRV_ENABLE);
    gpio_set_dir(DRV_ENABLE, GPIO_OUT);
    gpio_put(DRV_ENABLE, 0);

    /* Clear shift registers */
    gpio_put(SR_LATCH, 0);
    for (int i = 0; i < 16; i++) {
        gpio_put(SR_DATA, 0);
        gpio_put(SR_CLK, 1);
        sleep_us(1);
        gpio_put(SR_CLK, 0);
    }
    gpio_put(SR_LATCH, 1);
    sleep_us(1);
    gpio_put(SR_LATCH, 0);

    s_init_done = true;
}

static void shift_out_16(uint16_t data)
{
    /* MSB first */
    for (int i = 15; i >= 0; i--) {
        gpio_put(SR_DATA, (data >> i) & 1);
        gpio_put(SR_CLK, 1);
        sleep_us(1);
        gpio_put(SR_CLK, 0);
    }
    /* Latch */
    gpio_put(SR_LATCH, 1);
    sleep_us(2);
    gpio_put(SR_LATCH, 0);
}

void emboss_fire_cell(uint8_t dots)
{
    if (!s_init_done) return;

    /* dots: bit0=dot1 ... bit7=dot8
     * Map to solenoid channels. For a single-cell emboss,
     * we use column A (shift register bits 0-7).
     *
     * The force level scales the dwell time (not the current),
     * since solenoid force is proportional to activation time
     * within the impulse regime.
     */
    uint16_t sr_data = (uint16_t)dots; /* bits 0-7 = column A */

    /* Shift out the pattern */
    shift_out_16(sr_data);

    /* Enable DRV8833 drivers for the dwell period */
    uint16_t dwell = SOLID_DWELL_MS + (g_config.force * 2); /* 20-38ms */
    gpio_put(DRV_ENABLE, 1);
    sleep_ms(dwell);
    gpio_put(DRV_ENABLE, 0);

    /* Clear shift registers (all solenoids off) */
    shift_out_16(0);

    /* Recovery time for solenoid springs */
    sleep_ms(SOLID_RELEASE_MS);
}

void emboss_wait(void)
{
    /* No-op: the emboss_fire_cell function is blocking */
}