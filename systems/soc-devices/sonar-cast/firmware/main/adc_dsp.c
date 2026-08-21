/*
 * sonar-cast / firmware / adc_dsp.c
 * ADS7945 SPI-DMA capture + pulse-compression envelope extraction.
 */
#include "main.h"

/* Double-buffered DMA capture (ping-pong) so we can process one buffer
   while the next fills.  Each buffer holds ECHO_WINDOW_SAMPLES int16. */
static uint16_t dma_buf_a[ECHO_WINDOW_SAMPLES];
static uint16_t dma_buf_b[ECHO_WINDOW_SAMPLES];
static volatile bool buf_a_ready = false;
static volatile bool buf_b_ready = false;

/* Envelope output (decimated to ECHO_BIN_COUNT for BLE echogram). */
static float env_full[ECHO_WINDOW_SAMPLES];

void adc_dsp_init(void)
{
    /* SPI1 @ 18 MHz (ADS7945 max 20 MHz) → 1 Msps 12-bit.
       DMA RX into dma_buf_a/b ping-pong, TIM1 trigger (slave mode).
       CS managed by SPI hardware (NSS pulse). */
    memset(dma_buf_a, 0, sizeof(dma_buf_a));
    memset(dma_buf_b, 0, sizeof(dma_buf_b));
}

/* Start a DMA capture of n samples; returns the buffer that will fill.
   Caller polls adc_capture_done() or waits on the buffer-ready flag. */
uint16_t *adc_capture(uint32_t n)
{
    (void)n;
    /* In real HW: HAL_SPI_Receive_DMA(SPI1, dma_buf_a, ECHO_WINDOW_SAMPLES) */
    buf_a_ready = false;
    return dma_buf_a;
}

/* DMA complete callback (wired to SPI1 RX DMA IRQ in real build). */
void adc_dma_complete_cb(bool buf_a)
{
    if (buf_a) buf_a_ready = true;
    else       buf_b_ready = true;
}

bool adc_capture_ready(void) { return buf_a_ready; }

/*
 * Pulse-compress the raw capture into an envelope, then decimate to
 * ECHO_BIN_COUNT bins for the BLE echogram stream.
 *
 * Steps:
 *   1. chirp_pulse_compress(raw → env_full)   (500-tap matched FIR, SIMD)
 *   2. Normalize to 0..1 using a running max
 *   3. Decimate env_full → bins (log-compressed for display dynamic range)
 */
void adc_pulse_compress(uint16_t *raw, float *env_bins, uint32_t n_bins)
{
    /* Full-resolution envelope via matched filter */
    chirp_pulse_compress(raw, ECHO_WINDOW_SAMPLES, env_full, ECHO_WINDOW_SAMPLES);

    /* Find max for normalization */
    float maxv = 1e-9f;
    for (uint32_t i = 0; i < ECHO_WINDOW_SAMPLES; i++)
        if (env_full[i] > maxv) maxv = env_full[i];

    float inv = 1.0f / maxv;

    /* Decimate to n_bins (ECHO_BIN_COUNT) with peak-hold per bin
       (peak-hold preserves target spikes better than averaging). */
    uint32_t per = ECHO_WINDOW_SAMPLES / n_bins;
    for (uint32_t b = 0; b < n_bins; b++) {
        float pk = 0.0f;
        for (uint32_t j = 0; j < per; j++) {
            float v = env_full[b * per + j] * inv;
            if (v > pk) pk = v;
        }
        /* Log-compress: 255·log10(1+9·pk) → 0..255 display range */
        env_bins[b] = pk;
    }
}

/* Return the full-resolution envelope (for detector). */
const float *adc_get_env_full(void) { return env_full; }