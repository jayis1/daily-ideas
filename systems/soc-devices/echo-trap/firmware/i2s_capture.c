/*
 * i2s_capture.c — Dual-channel I2S MEMS microphone capture
 *
 * Uses ESP32-S3 I2S1 peripheral in Philips/standard mode to read two
 * ICS-43434 digital MEMS microphones (data on GPIO0 and GPIO1 in TDM
 * dual-slot mode). DMA double-buffering hands 250 ms windows to the
 * capture task via a queue.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "config.h"
#include "i2s_capture.h"
#include "esp_log.h"
#include "driver/i2s_std.h"

static const char *TAG = "i2s_capture";

static QueueHandle_t s_frame_queue;
static i2s_chan_handle_t s_rx_handle = NULL;

/* Double-buffer for DMA → frame assembly */
static int16_t s_dma_buf[WINDOW_SAMPLES * I2S_CHANNELS];
static audio_frame_t s_current_frame;

/* ISR callback: a DMA buffer has been received */
static bool IRAM_ATTR i2s_rx_callback(i2s_chan_handle_t handle,
                                       i2s_event_data_t *event,
                                       void *user_ctx)
{
    (void)handle; (void)event; (void)user_ctx;
    BaseType_t hpw = pdFALSE;

    /* Deinterleave: DMA buffer is [L0, R0, L1, R1, ...] (32-bit slots, top 16 bits valid) */
    for (int i = 0; i < WINDOW_SAMPLES; i++) {
        s_current_frame.mic1[i] = s_dma_buf[i * 2];
        s_current_frame.mic2[i] = s_dma_buf[i * 2 + 1];
    }
    s_current_frame.timestamp_us = esp_timer_get_time();

    /* Send to queue from ISR */
    xQueueSendFromISR(s_frame_queue, &s_current_frame, &hpw);
    return hpw == pdTRUE;
}

void i2s_capture_init(void)
{
    ESP_LOGI(TAG, "Initializing dual ICS-43434 I2S capture (%d kHz, %d ch)",
             I2S_SAMPLE_RATE_HZ / 1000, I2S_CHANNELS);

    /* Create the frame queue (double-buffered — 2 frames) */
    s_frame_queue = xQueueCreate(FRAMES_DOUBLE_BUF, sizeof(audio_frame_t));

    /* Configure I2S channel */
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1,
                                                             I2S_ROLE_MASTER);
    chan_cfg.dma_desc_num   = I2S_DMA_BUF_COUNT;
    chan_cfg.dma_frame_num  = I2S_DMA_BUF_LEN;
    chan_cfg.dma_buf        = NULL;  /* let driver allocate */
    ESP_ERROR_CHECK(i2s_new_channel(&chan_cfg, NULL, &s_rx_handle));

    /* Standard (Philips) I2S format */
    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(I2S_SAMPLE_RATE_HZ),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                         I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .bclk = PIN_I2S_SCK,
            .ws   = PIN_I2S_WS,
            .dout = -1,   /* not used (mics are input only) */
            .din  = PIN_I2S_SD1,
            .mclk = -1,
        },
    };
    /* Configure both data inputs — ICS-43434 outputs on GPIO0 and GPIO1 */
    std_cfg.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT | I2S_STD_SLOT_RIGHT;
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(s_rx_handle, &std_cfg));

    /* Register ISR callback for DMA buffer completion */
    i2s_event_callbacks_t cbs = {
        .on_recv = i2s_rx_callback,
        .on_recv_q_ovf = NULL,
        .on_sent = NULL,
        .on_send_q_ovf = NULL,
    };
    ESP_ERROR_CHECK(i2s_register_event_callback(s_rx_handle, &cbs, NULL));

    /* Start receiving */
    ESP_ERROR_CHECK(i2s_channel_enable(s_rx_handle));
    ESP_LOGI(TAG, "I2S capture running — 250 ms windows, double-buffered");
}

BaseType_t i2s_capture_get_frame(audio_frame_t *frame, TickType_t timeout)
{
    return xQueueReceive(s_frame_queue, frame, timeout);
}