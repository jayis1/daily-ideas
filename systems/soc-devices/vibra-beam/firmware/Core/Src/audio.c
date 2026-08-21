/*
 * audio.c — heterodyne-to-audio (I2S MAX98357A)
 *
 * Translates the velocity (mm/s) time series into the audible band
 * by scaling the phase rate and writing 16-bit samples to the I2S
 * amplifier at 44.1 kHz. The user "listens" to the vibration.
 */

#include "audio.h"
#include "stm32g4xx_hal.h"
#include "config.h"
#include <math.h>

extern I2S_HandleTypeDef hi2s2;

static uint8_t  s_active = 0;
static float    s_gain = CONFIG_AUDIO_GAIN_DEFAULT;
static float    s_shift = CONFIG_AUDIO_SHIFT_DEFAULT;
static int16_t  s_audio_buf[256];
static uint32_t s_write_idx = 0;

void audio_init(void)
{
    /* I2S already initialized in main */
}

void audio_start(void)
{
    s_active = 1;
    s_write_idx = 0;
    HAL_I2S_Transmit_DMA(&hi2s2, (uint16_t *)s_audio_buf, 256);
}

void audio_stop(void)
{
    s_active = 0;
    HAL_I2S_DMAPause(&hi2s2);
}

void audio_set_gain(float g) { s_gain = g; }
void audio_set_shift(float s) { s_shift = s; }

void audio_push_velocity(float vel_mms)
{
    if (!s_active) return;
    /* Scale and clip to 16-bit */
    float v = vel_mms * s_gain * s_shift;
    if (v > 32767.0f) v = 32767.0f;
    if (v < -32768.0f) v = -32768.0f;
    s_audio_buf[s_write_idx++] = (int16_t)v;
    if (s_write_idx >= 256) s_write_idx = 0;
}