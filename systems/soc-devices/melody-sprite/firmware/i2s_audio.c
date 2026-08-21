/*
 * Melody Sprite — RP2040 FM Synthesizer
 * i2s_audio.c — I2S audio output via PIO for PCM5102A DAC
 *
 * Uses RP2040 PIO to generate I2S BCLK, LRCK, and DOUT signals.
 * Audio data is pushed via DMA from the synthesis engine's output buffer.
 */

#include "i2s_audio.h"
#include <string.h>

/* Pico SDK headers (would be included in real build) */
// #include "hardware/pio.h"
// #include "hardware/dma.h"
// #include "hardware/clocks.h"
// #include "i2s.pio.h"

/*
 * PIO program for I2S output:
 *
 * ; I2S transmitter — 16-bit stereo, MSB first
 * ; Side-set: BCLK on GPIO4
 * ; Out: DOUT on GPIO6
 * ; LRCK toggled by ISR
 *
 * .program i2s_out
 * .side_set 1
 * .origin 0
 *
 * pull side 0          ; Load next 32-bit word, BCLK low
 * out null, 16 side 1  ; Discard upper 16 bits (or right channel), BCLK high
 * out pins, 16 side 1  ; Shift out 16 bits left channel, BCLK high
 *                        ; LRCK toggles every 16 BCLK edges
 *
 * The PIO runs at BCLK × 2 = 44100 × 32 × 2 = 2,822,400 Hz
 */

/* State */
static bool i2s_running = false;
static uint8_t i2s_volume_percent = 100;
static bool i2s_muted = false;

/* DMA channel handles */
static int dma_chan[2] = {0, 1};
static volatile int active_dma_buf = 0;

/* Audio DMA buffers (stereo interleaved, 16-bit) */
static int16_t dma_buf[2][I2S_BUFFER_SIZE * 2];

/* Volume table (linear → perceptual) */
static int16_t volume_lut[101]; /* 0–100% */

static void build_volume_lut(void)
{
    for (int i = 0; i <= 100; i++) {
        /* Exponential volume curve for perceptual linearity */
        float linear = (float)i / 100.0f;
        float perceptual = powf(linear, 2.0f); /* square law */
        volume_lut[i] = (int16_t)(perceptual * 32767.0f);
    }
}

void i2s_init(void)
{
    build_volume_lut();

    /*
     * Real implementation would:
     *
     * 1. Load i2s_out PIO program into a PIO state machine
     * 2. Configure side-set pin for BCLK (GPIO4)
     * 3. Configure OUT pin for DOUT (GPIO6)
     * 4. Set LRCK pin (GPIO5) as GPIO output, toggled by PIO ISR
     * 5. Configure PIO clock divider for 44.1kHz × 32 × 2
     * 6. Claim DMA channels
     * 7. Configure DMA: 32-bit transfers, PIO TX FIFO destination
     * 8. Chain DMA channels for ping-pong buffering
     * 9. Set PCM5102A to I2S mode (hardware pins: FMT=GND, SCK=GND)
     */

    /* PIO clock divider calculation:
     * System clock = 133 MHz (typical)
     * PIO clock = BCLK × 2 = 44100 × 32 × 2 = 2,822,400 Hz
     * Divider = 133,000,000 / 2,822,400 ≈ 47.13
     * => Use clkdiv = 47 (slight sample rate deviation, acceptable)
     *
     * For exact 44.1kHz, we'd use system clock = 135,475,200 Hz
     * or adjust PIO divider dynamically with fractional component.
     */

    i2s_running = false;
    i2s_volume_percent = 100;
    i2s_muted = false;
}

void i2s_start(void)
{
    /* Enable PIO state machine and DMA */
    i2s_running = true;

    /* In real implementation:
     * - Start PIO SM
     * - Enable DMA channels
     * - Write initial buffer to prevent underrun
     */
}

void i2s_stop(void)
{
    i2s_running = false;

    /* In real implementation:
     * - Abort DMA channels
     * - Stop PIO SM
     * - Drive DOUT low (mute)
     */
}

static void apply_volume(int16_t *buf, int num_samples)
{
    if (i2s_muted) {
        memset(buf, 0, num_samples * sizeof(int16_t));
        return;
    }

    if (i2s_volume_percent >= 100) return; /* Full volume, no scaling */

    int16_t scale = volume_lut[i2s_volume_percent];
    for (int i = 0; i < num_samples; i++) {
        /* Multiply by volume scale and shift back */
        buf[i] = (int16_t)(((int32_t)buf[i] * scale) >> 15);
    }
}

int i2s_push_buffer(const int16_t *samples, int num_frames)
{
    if (!i2s_running) return -1;

    int next_buf = 1 - active_dma_buf;

    /* Copy and apply volume */
    memcpy(dma_buf[next_buf], samples, num_frames * 2 * sizeof(int16_t));
    apply_volume(dma_buf[next_buf], num_frames * 2);

    /* In real implementation:
     * - Check if DMA channel is available
     * - Configure DMA transfer from dma_buf[next_buf] to PIO TX FIFO
     * - Start DMA
     * - Swap active_dma_buf
     */

    active_dma_buf = next_buf;
    return 0;
}

bool i2s_buffer_available(void)
{
    /* In real implementation: check if either DMA channel has completed */
    return i2s_running;
}

void i2s_set_volume(uint8_t percent)
{
    if (percent > 100) percent = 100;
    i2s_volume_percent = percent;
}

void i2s_mute(bool mute)
{
    i2s_muted = mute;
    /* In real implementation: also set XSMT pin on PCM5102A low to mute */
}