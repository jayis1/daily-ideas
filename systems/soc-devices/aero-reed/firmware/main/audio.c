/*
 * audio.c — I2S stereo 44.1 kHz 16-bit → PCM5102A
 *
 * GPIO mapping:
 *   BCK  = GPIO35
 *   WS   = GPIO36
 *   DOUT = GPIO37
 */
#include "audio.h"
#include "driver/i2s_std.h"
#include "esp_log.h"

static const char *TAG = "audio";
static i2s_chan_handle_t tx_handle = NULL;

void audio_init(void)
{
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    chan_cfg.dma_desc_num = 6;
    chan_cfg.dma_frame_num = 240;  /* 240 stereo frames per descriptor */
    i2s_new_channel(&chan_cfg, &tx_handle, NULL);

    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(44100),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT,
                                                          I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .bck = 35, .ws = 36, .dout = 37,
            .din = -1, .mclk = -1,
        },
    };
    i2s_channel_init_std_mode(tx_handle, &std_cfg);
    i2s_channel_enable(tx_handle);
    ESP_LOGI(TAG, "I2S @ 44100 Hz stereo 16-bit ready → PCM5102A");
}

void audio_write_block(const int16_t *data, size_t bytes)
{
    size_t written = 0;
    i2s_channel_write(tx_handle, (void *)data, bytes, &written, portMAX_DELAY);
    if (written != bytes) {
        ESP_LOGW(TAG, "I2S underrun: wrote %u/%u", (unsigned)written, (unsigned)bytes);
    }
}