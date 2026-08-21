/**
 * i2s_manager.c — Dual I²S bus manager
 *
 * Uses ESP-IDF I2S driver in duplex mode for I2S0 (speaker TX + mic L RX)
 * and simplex mode for I2S1 (mic R RX).
 *
 * DMA buffers are allocated in PSRAM for long captures (up to 30s at 48kHz).
 */

#include "i2s_manager.h"
#include <string.h>
#include <stdlib.h>
#include "esp_log.h"
#include "driver/i2s_std.h"
#include "soc/i2s_struct.h"

static const char *TAG = "i2s_mgr";

/* I2S port assignments */
#define I2S0_PORT   I2S_NUM_0    /* Speaker TX + Mic L RX */
#define I2S1_PORT   I2S_NUM_1    /* Mic R RX */

/* GPIO assignments (from pin table) */
#define I2S_MCLK    1
#define I2S0_BCLK   2
#define I2S0_WS     3
#define I2S0_DIN   4   /* Mic L data in */
#define I2S0_DOUT  5   /* Speaker data out */
#define I2S1_BCLK   6
#define I2S1_WS     7
#define I2S1_DIN   8   /* Mic R data in */

/* DMA buffer configuration */
#define I2S_DMA_BUF_COUNT  16
#define I2S_DMA_BUF_SIZE   1024   /* samples per buffer */

/* Capture state */
static bool capturing = false;
static int16_t *capture_buf_l = NULL;
static int16_t *capture_buf_r = NULL;
static volatile uint32_t capture_write_idx = 0;
static uint32_t capture_total_samples = 0;

/* I2S channel handles */
static i2s_chan_handle_t rx_handle_0 = NULL;
static i2s_chan_handle_t tx_handle_0 = NULL;
static i2s_chan_handle_t rx_handle_1 = NULL;

int i2s_manager_init(void) {
    ESP_LOGI(TAG, "Initializing dual I²S buses");

    /* ---- I2S0: Duplex (TX speaker + RX mic L) ---- */
    i2s_chan_handle_t tx_chan, rx_chan;
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    chan_cfg.dma_desc_num = I2S_DMA_BUF_COUNT;
    chan_cfg.dma_frame_num = I2S_DMA_BUF_SIZE;

    /* Create TX channel (speaker) */
    i2s_new_channel(&chan_cfg, &tx_chan, NULL);
    tx_handle_0 = tx_chan;

    /* Create RX channel (mic L) — on same port */
    i2s_chan_config_t rx_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    rx_cfg.dma_desc_num = I2S_DMA_BUF_COUNT;
    rx_cfg.dma_frame_num = I2S_DMA_BUF_SIZE;
    i2s_new_channel(&rx_cfg, NULL, &rx_chan);
    rx_handle_0 = rx_chan;

    /* Configure I2S0 standard mode */
    i2s_std_config_t std_cfg0 = {
        .clk_cfg = {
            .sample_rate_hz = 48000,
            .clk_src = I2S_CLK_SRC_DEFAULT,
            .mclk_multiple = I2S_MCLK_MULTIPLE_256,
        },
        .slot_cfg = {
            .data_bit_width = I2S_DATA_BIT_WIDTH_16BIT,
            .slot_bit_width = I2S_SLOT_BIT_WIDTH_16BIT,
            .slot_mode = I2S_SLOT_MODE_STEREO,
            .slot_mask = I2S_STD_SLOT_BOTH,
        },
        .gpio_cfg = {
            .mclk = I2S_MCLK,
            .bclk = I2S0_BCLK,
            .ws   = I2S0_WS,
            .dout = I2S0_DOUT,
            .din  = I2S0_DIN,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };

    i2s_channel_init_std_mode(tx_chan, &std_cfg0);
    i2s_channel_init_std_mode(rx_chan, &std_cfg0);

    /* ---- I2S1: RX only (mic R) ---- */
    i2s_chan_config_t chan_cfg1 = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
    chan_cfg1.dma_desc_num = I2S_DMA_BUF_COUNT;
    chan_cfg1.dma_frame_num = I2S_DMA_BUF_SIZE;
    i2s_new_channel(&chan_cfg1, NULL, &rx_chan);
    rx_handle_1 = rx_chan;

    i2s_std_config_t std_cfg1 = {
        .clk_cfg = {
            .sample_rate_hz = 48000,
            .clk_src = I2S_CLK_SRC_DEFAULT,
            .mclk_multiple = I2S_MCLK_MULTIPLE_256,
        },
        .slot_cfg = {
            .data_bit_width = I2S_DATA_BIT_WIDTH_16BIT,
            .slot_bit_width = I2S_SLOT_BIT_WIDTH_16BIT,
            .slot_mode = I2S_SLOT_MODE_MONO,
            .slot_mask = I2S_STD_SLOT_LEFT,
        },
        .gpio_cfg = {
            .mclk = I2S_MCLK,  /* Share MCLK with I2S0 */
            .bclk = I2S1_BCLK,
            .ws   = I2S1_WS,
            .dout = I2S_GPIO_UNUSED,
            .din  = I2S1_DIN,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };

    i2s_channel_init_std_mode(rx_chan, &std_cfg1);

    ESP_LOGI(TAG, "I²S buses initialized (I2S0=duplex, I2S1=RX-only)");
    return 0;
}

int i2s_manager_start_capture(uint32_t sample_rate) {
    if (capturing) {
        ESP_LOGW(TAG, "Already capturing");
        return 0;
    }

    capture_total_samples = sample_rate * 30;  /* Max 30 seconds */
    capture_buf_l = malloc(capture_total_samples * sizeof(int16_t));
    capture_buf_r = malloc(capture_total_samples * sizeof(int16_t));

    if (!capture_buf_l || !capture_buf_r) {
        ESP_LOGE(TAG, "Capture buffer alloc failed (%u samples each)",
                 capture_total_samples);
        free(capture_buf_l); free(capture_buf_r);
        return -1;
    }

    capture_write_idx = 0;
    capturing = true;

    /* Enable both RX channels */
    i2s_channel_enable(rx_handle_0);
    i2s_channel_enable(rx_handle_1);

    /* Enable TX for speaker output */
    i2s_channel_enable(tx_handle_0);

    /* Start capture task */
    ESP_LOGI(TAG, "Capture started at %u Hz", sample_rate);
    return 0;
}

/**
 * Background capture loop — called periodically from main loop or RTOS task.
 * Reads DMA buffers and stores into capture_buf.
 */
static void capture_chunk(void) {
    if (!capturing) return;

    int16_t tmp_l[I2S_DMA_BUF_SIZE];
    int16_t tmp_r[I2S_DMA_BUF_SIZE];
    size_t bytes_read_l = 0, bytes_read_r = 0;

    /* Read from I2S0 RX (mic L) */
    i2s_channel_read(rx_handle_0, tmp_l, sizeof(tmp_l), &bytes_read_l, 0);

    /* Read from I2S1 RX (mic R) */
    i2s_channel_read(rx_handle_1, tmp_r, sizeof(tmp_r), &bytes_read_r, 0);

    size_t samples_l = bytes_read_l / sizeof(int16_t);
    size_t samples_r = bytes_read_r / sizeof(int16_t);
    size_t to_store = (samples_l < samples_r) ? samples_l : samples_r;

    /* Store in capture buffers */
    if (capture_write_idx + to_store <= capture_total_samples) {
        memcpy(&capture_buf_l[capture_write_idx], tmp_l, to_store * sizeof(int16_t));
        memcpy(&capture_buf_r[capture_write_idx], tmp_r, to_store * sizeof(int16_t));
        capture_write_idx += to_store;
    }
}

int i2s_manager_read_captured(int16_t *out_l, int16_t *out_r,
                               uint32_t num_samples) {
    if (!capturing) return -1;

    /* Stop capturing */
    i2s_channel_disable(rx_handle_0);
    i2s_channel_disable(rx_handle_1);
    i2s_channel_disable(tx_handle_0);
    capturing = false;

    /* Copy to caller buffers */
    uint32_t to_copy = (num_samples < capture_write_idx) ?
                        num_samples : capture_write_idx;
    if (out_l && capture_buf_l)
        memcpy(out_l, capture_buf_l, to_copy * sizeof(int16_t));
    if (out_r && capture_buf_r)
        memcpy(out_r, capture_buf_r, to_copy * sizeof(int16_t));

    /* Free internal capture buffers */
    free(capture_buf_l);
    free(capture_buf_r);
    capture_buf_l = NULL;
    capture_buf_r = NULL;

    ESP_LOGI(TAG, "Capture complete: %u samples", to_copy);
    return 0;
}

int i2s_manager_write_speaker(const uint8_t *data, size_t len) {
    if (!tx_handle_0) return -1;

    size_t bytes_written = 0;
    i2s_channel_write(tx_handle_0, data, len, &bytes_written, 100);
    return (int)bytes_written;
}

void i2s_manager_stop_capture(void) {
    if (!capturing) return;

    i2s_channel_disable(rx_handle_0);
    i2s_channel_disable(rx_handle_1);
    i2s_channel_disable(tx_handle_0);
    capturing = false;

    free(capture_buf_l);
    free(capture_buf_r);
    capture_buf_l = NULL;
    capture_buf_r = NULL;

    ESP_LOGI(TAG, "Capture stopped");
}