/*
 * Levia Forge — PIO Phase Serial Stream Generator
 *
 * PIO0 SM0 generates a continuous serial bitstream at 10.24 MHz
 * (256× oversampling of 40 kHz carrier). The data comes from a
 * DMA channel that reads the phase_buffer (2304 bytes) in a loop.
 *
 * The PIO shifts out 72 bits per 40 kHz cycle, with a latch pulse
 * at the end of each cycle.
 *
 * Pin mapping:
 *   GP0 = DATA  (serial bit output)
 *   GP1 = CLOCK (10.24 MHz shift clock)
 *   GP2 = LATCH (40 kHz latch pulse, 1 cycle wide)
 *   GP3 = BLANK (OE control, manual GPIO)
 *
 * SPDX-License-Identifier: MIT
 */
#include "phase_engine.h"
#include "phase_compute.h"
#include "sdkconfig.h"
#include "pio_phase.pio.h"
#include "pico/stdlib.h"
#include "hardware/pio.h"
#include "hardware/dma.h"
#include "hardware/clocks.h"
#include "hardware/irq.h"
#include <string.h>

static int dma_chan_data;
static int dma_chan_wrap;
static volatile bool dma_underrun;
static volatile uint32_t dma_cycle_count;

/*
 * PIO program (pio_phase.pio):
 *
 * .program phase_stream
 * .side_set 2          ; CLOCK and LATCH as side-set pins
 * .wrap_target
 *     out pins, 1      side 0b00   ; shift out 1 bit, CLOCK low
 *     out pins, 1      side 0b01   ; shift out 1 bit, CLOCK high (rising edge)
 *     ...              (repeated for each bit)
 * .wrap
 *
 * Actually, the PIO is simpler than that. We use:
 *
 * .program phase_stream
 * .side_set 2
 * .wrap_target
 *     out pins, 1      side 0  ; data out, clock low
 *     jmp 0            side 1  ; clock high (latch data into 595 on rising edge)
 * .wrap
 *
 * But we need a latch pulse every 72 bits. We use a second PIO SM
 * or handle latching in software via DMA transfer count interrupt.
 *
 * Simplified approach: PIO just shifts data at 10.24 MHz.
 * We generate the latch pulse via a separate PIO SM or PWM slice
 * at 40 kHz. The 74HC595 latches on RCLK rising edge.
 */

static PIO pio = pio0;
static uint sm = 0;

void phase_engine_init(void)
{
    /* Load the PIO program */
    uint offset = pio_add_program(pio, &phase_stream_program);

    /* Configure PIO state machine */
    pio_sm_config c = phase_stream_program_get_default_config(pio, offset);

    /* Set up pins: DATA on GP0, CLOCK+LATCH as side-set on GP1/GP2 */
    sm_config_set_out_pins(&c, PIN_PIO_DATA, 1);
    sm_config_set_sideset_pins(&c, PIN_PIO_CLOCK);

    /* Set up the output shift register: shift to left (MSB first? or
     * LSB first? 74HC595 shifts on rising edge of SRCLK, data on SER.
     * We want to shift 72 bits per 40 kHz cycle. */
    sm_config_set_out_shift(&c, true, false, 32);  /* LSB first, no autopull */

    /* Enable autopull at 32 bits so DMA can feed 4-byte words */
    sm_config_set_out_shift(&c, true, true, 32);

    /* Set clock divider: we want 10.24 MHz bit clock.
     * RP2040 system clock = 133 MHz.
     * Div = sys_clk / (PIO_clock × cycles_per_instruction)
     * Each out+side takes 1 cycle, so PIO_clock = sys_clk / div
     * For 10.24 MHz: div = 133e6 / 10.24e6 ≈ 12.998
     * But actually we need 2 PIO cycles per bit (out + jmp for clock).
     * So bit rate = PIO_clock / 2.
     * For 10.24 MHz bit rate: PIO_clock = 20.48 MHz
     * div = 133e6 / 20.48e6 ≈ 6.494
     */
    float div = (float)clock_get_hz(clk_sys) / (PIO_CLOCK_HZ * 2.0f);
    sm_config_set_clkdiv(&c, div);

    /* Initialize the state machine */
    pio_sm_init(pio, sm, offset, &c);

    /* Set pin directions */
    pio_sm_set_set_pins(pio, sm, PIN_PIO_DATA, 1);
    pio_gpio_init(pio, PIN_PIO_DATA);
    gpio_set_dir(PIN_PIO_DATA, GPIO_OUT);

    pio_sm_set_set_pins(pio, sm, PIN_PIO_CLOCK, 2);
    pio_gpio_init(pio, PIN_PIO_CLOCK);
    pio_gpio_init(pio, PIN_PIO_LATCH);
    gpio_set_dir(PIN_PIO_CLOCK, GPIO_OUT);
    gpio_set_dir(PIN_PIO_LATCH, GPIO_OUT);

    /* BLANK pin (OE control) — manual GPIO */
    gpio_init(PIN_PIO_BLANK);
    gpio_set_dir(PIN_PIO_BLANK, GPIO_OUT);
    gpio_put(PIN_PIO_BLANK, 1);  /* Start blanked (transducers off) */

    /* Set up DMA channel for data transfer */
    dma_chan_data = dma_claim_unused_channel(true);
    dma_chan_wrap = dma_claim_unused_channel(true);

    /* DMA channel 0: transfer from phase_buffer to PIO TX FIFO */
    dma_channel_config dcfg = dma_channel_get_default_config(dma_chan_data);
    channel_config_set_transfer_data_size(&dcfg, DMA_SIZE_32);
    channel_config_set_read_increment(&dcfg, true);   /* read from buffer */
    channel_config_set_write_increment(&dcfg, false);  /* write to PIO FIFO */
    channel_config_set_dreq(&dcfg, pio_get_dreq(pio, sm, true));  /* PIO TX DREQ */
    channel_config_set_chain_to(&dcfg, dma_chan_wrap);  /* chain to wrap channel */

    /* DMA channel 1: re-trigger channel 0 (wrap around) */
    dma_channel_config wcfg = dma_channel_get_default_config(dma_chan_wrap);
    channel_config_set_transfer_data_size(&wcfg, DMA_SIZE_32);
    channel_config_set_read_increment(&wcfg, false);
    channel_config_set_write_increment(&wcfg, false);
    channel_config_set_dreq(&wcfg, DREQ_FORCE);  /* immediate */

    /* Configure the latch pulse: we need a 40 kHz pulse on GP2.
     * We use a PWM slice for this. */
    /* PWM for LATCH: 40 kHz, duty = 1/256 (short pulse) */
    gpio_set_function(PIN_PIO_LATCH, GPIO_FUNC_PWM);
    uint latch_slice = pwm_gpio_to_slice_num(PIN_PIO_LATCH);
    pwm_config pwmcfg = pwm_get_default_config();
    /* 133 MHz / 40 kHz = 3325. Wrap = 3325, CC = 1 (short pulse) */
    pwm_config_set_wrap(&pwmcfg, 3325);
    pwm_config_set_clkdiv(&pwmcfg, 1.0f);
    pwm_init(latch_slice, &pwmcfg, true);
    pwm_set_chan_level(latch_slice, pwm_gpio_to_channel(PIN_PIO_LATCH), 1);

    dma_underrun = false;
    dma_cycle_count = 0;
}

void phase_engine_start(void)
{
    /* Start the DMA transfer (circular) */
    uint8_t *buf = phase_get_buffer();
    int buf_words = DMA_BUFFER_SIZE / 4;

    /* Channel 1: writes the read address + transfer count to channel 0,
     * re-triggering it. This creates an infinite loop. */
    dma_channel_configure(
        dma_chan_wrap,
        &dma_channel_get_default_config(dma_chan_wrap),
        &dma_hw->ch[dma_chan_data].al1_read_addr,
        &buf,  /* address of the read pointer (will be set to buf) */
        1,     /* 1 transfer: write the read_addr */
        false  /* don't start yet */
    );

    /* Actually, for a simple circular buffer, we use the DMA ring mode:
     * Set READ_ADDR to buffer start, TRANS_COUNT = buf_words,
     * and enable ring mode (wrap at buffer size). */
    dma_channel_configure(
        dma_chan_data,
        NULL,  /* use config from init */
        &pio->txf[sm],       /* write to PIO TX FIFO */
        buf,                 /* read from phase buffer */
        buf_words,           /* 2304/4 = 576 words */
        true                 /* start immediately */
    );

    /* Enable ring wrap on the data channel: wrap at 2304 bytes = 2^? 
     * 2304 is not a power of 2. So we use the chain-to approach instead.
     * The chain_to on channel 0 triggers channel 1, which reconfigures
     * channel 0. But for simplicity, we just use TRANS_COUNT = large
     * and restart on interrupt.
     *
     * Alternative: Use DMA ring buffer with size = 2048 (closest power
     * of 2 < 2304). Not ideal.
     *
     * Best approach: Use IRQ on channel 0 completion to restart. */
    dma_channel_set_irq0_enabled(dma_chan_data, true);
    irq_set_exclusive_handler(DMA_IRQ_0, phase_engine_dma_irq);
    irq_set_enabled(DMA_IRQ_0, true);

    /* Start the PIO state machine */
    pio_sm_set_enabled(pio, sm, true);

    /* Unblank the transducers */
    gpio_put(PIN_PIO_BLANK, 0);
}

void phase_engine_stop(void)
{
    /* Blank the transducers immediately */
    gpio_put(PIN_PIO_BLANK, 1);

    /* Stop the PIO state machine */
    pio_sm_set_enabled(pio, sm, false);

    /* Stop DMA */
    dma_channel_abort(dma_chan_data);
    dma_channel_abort(dma_chan_wrap);
}

void phase_engine_set_blank(bool blanked)
{
    gpio_put(PIN_PIO_BLANK, blanked ? 1 : 0);
}

bool phase_engine_is_underrun(void)
{
    return dma_underrun;
}

uint32_t phase_engine_get_cycles(void)
{
    return dma_cycle_count;
}

/*
 * DMA completion IRQ handler: restart the transfer from buffer start.
 */
void __not_in_flash_func(phase_engine_dma_irq)(void)
{
    dma_hw->ints0 = (1u << dma_chan_data);  /* clear IRQ flag */
    dma_cycle_count++;

    uint8_t *buf = phase_get_buffer();
    int buf_words = DMA_BUFFER_SIZE / 4;

    /* Restart the transfer */
    dma_channel_configure(
        dma_chan_data,
        NULL,
        &pio->txf[sm],
        buf,
        buf_words,
        true  /* start */
    );

    /* Check for PIO stall (underrun) */
    if (pio_sm_is_tx_fifo_full(pio, sm)) {
        dma_underrun = true;
    }
}