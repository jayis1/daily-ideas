/*
 * cor-sono / firmware / audio.c
 * I2S MEMS microphone (ICS-43434) + ADC piezo contact microphone
 * Core 0 task: continuously samples both channels at 4 kHz
 */
#include "main.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/ringbuf.h"
#include "driver/i2s_std.h"
#include "driver/adc.h"
#include "driver/adc_continuous.h"
#include "esp_adc_cal.h"
#include "string.h"

static const char *TAG = "audio";

/* I2S config for ICS-43434 */
static i2s_chan_handle_t rx_chan;

/* ADC config for piezo contact mic on GPIO8 = ADC1_CH7 */
#define PIEZO_ADC_UNIT    ADC_UNIT_1
#define PIEZO_ADC_CHANNEL ADC_CHANNEL_7
#define ADC_ATTEN         ADC_ATTEN_DB_12
#define ADC_FREQ          4000

/* Ring buffer of processed stereo audio for downstream consumers */
static RingbufHandle_t audio_ring;

/* Frame counter */
static volatile uint32_t g_frame_idx = 0;

uint32_t audio_frame_index(void) { return g_frame_idx; }
RingbufHandle_t audio_get_ring(void) { return audio_ring; }

/* ---- I2S init ---- */
static void i2s_mic_init(void)
{
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    i2s_new_channel(&chan_cfg, NULL, &rx_chan);

    i2s_std_config_t std_cfg = {
        .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_32BIT,
                                                        I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .bclk = 2, .ws = 1, .dout = -1, .din = 4,
            .mclk = -1,
        },
    };
    i2s_channel_init_std_mode(rx_chan, &std_cfg);
    i2s_channel_enable(rx_chan);
}

/* ---- ADC piezo init (continuous mode) ---- */
static adc_continuous_handle_t adc_handle;

static void adc_piezo_init(void)
{
    adc_continuous_handle_cfg_t cfg = { .buf_size = 1024, .buf_count = 4 };
    adc_continuous_new_handle(&cfg, &adc_handle);

    adc_digi_pattern_config_t pattern = {
        .atten = ADC_ATTEN, .channel = PIEZO_ADC_CHANNEL, .unit = 0, .bit_width = 12
    };
    adc_continuous_config_t dig_cfg = {
        .pattern_num = 1, .adc_pattern = &pattern,
        .sample_freq_hz = ADC_FREQ, .conv_mode = ADC_CONV_SINGLE_UNIT_1,
        .format = ADC_DIGI_FORMAT_12BIT,
    };
    adc_continuous_config(adc_handle, &dig_cfg);
    adc_continuous_start(adc_handle);
}

/* ---- Audio task ---- */
static int16_t piezo_scale(uint16_t raw)
{
    /* 12-bit ADC (0–4095) → 16-bit signed centered at 0 */
    return (int16_t)((int)raw - 2048) * 16;  /* scale ×16 for headroom */
}

/* Latest samples, accessible by pcg_task */
static int16_t g_contact[BLOCK_SAMPLES];
static int16_t g_ambient[BLOCK_SAMPLES];

void audio_get_block(int16_t *contact, int16_t *ambient)
{
    memcpy(contact, g_contact, sizeof(g_contact));
    memcpy(ambient, g_ambient, sizeof(g_ambient));
}

void audio_init(void)
{
    ESP_LOGI(TAG, "init I2S MEMS mic + ADC piezo");
    audio_ring = xRingbufferCreate(AUDIO_RING_LEN * 2 * sizeof(int16_t), RINGBUF_TYPE_BYTE);
    i2s_mic_init();
    adc_piezo_init();
}

void audio_task(void *arg)
{
    int32_t i2s_raw[BLOCK_SAMPLES];
    uint8_t adc_buf[1024];
    uint32_t bytes_read;

    while (1) {
        /* Read I²S ambient mic (32-bit slots → 16-bit) */
        size_t i2s_bytes = 0;
        i2s_channel_read(rx_chan, i2s_raw, sizeof(i2s_raw), &i2s_bytes, pdMS_TO_TICKS(50));
        size_t n = i2s_bytes / sizeof(int32_t);
        if (n > BLOCK_SAMPLES) n = BLOCK_SAMPLES;
        for (size_t i = 0; i < n; i++)
            g_ambient[i] = (int16_t)(i2s_raw[i] >> 14);  /* 32→16 bit */

        /* Read ADC piezo (continuous mode) */
        bytes_read = 0;
        esp_err_t r = adc_continuous_read(adc_handle, adc_buf, sizeof(adc_buf),
                                           &bytes_read, pdMS_TO_TICKS(50));
        if (r == ESP_OK) {
            uint32_t samples = bytes_read / sizeof(adc_digi_output_data_t);
            if (samples > BLOCK_SAMPLES) samples = BLOCK_SAMPLES;
            for (uint32_t i = 0; i < samples; i++) {
                adc_digi_output_data_t *d = (adc_digi_output_data_t *)(adc_buf + i * sizeof(adc_digi_output_data_t));
                g_contact[i] = piezo_scale(d->type2.data);
            }
        }

        g_frame_idx++;

        /* Send stereo block to ring buffer for downstream consumers */
        int16_t stereo[BLOCK_SAMPLES * 2];
        for (int i = 0; i < BLOCK_SAMPLES; i++) {
            stereo[i * 2]     = g_contact[i];
            stereo[i * 2 + 1] = g_ambient[i];
        }
        xRingbufferSend(audio_ring, stereo, sizeof(stereo), 0);
    }
}