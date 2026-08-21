/*
 * Melody Sprite — RP2040 FM Synthesizer
 * i2s_audio.h — I2S audio output driver for PCM5102A DAC
 */

#ifndef I2S_AUDIO_H
#define I2S_AUDIO_H

#include <stdint.h>
#include "synth_engine.h"

#define I2S_SAMPLE_RATE  44100
#define I2S_BITS_PER_SAMPLE  16
#define I2S_CHANNELS      2     /* Stereo */
#define I2S_BUFFER_COUNT  4     /* Double-buffered × 2 */
#define I2S_BUFFER_SIZE   BUFFER_SIZE

/* RP2040 GPIO pins for I2S */
#define I2S_BCLK_PIN  4
#define I2S_LRCK_PIN  5
#define I2S_DOUT_PIN   6

/* Initialize I2S peripheral and PIO state machine */
void i2s_init(void);

/* Start I2S output (begin pushing audio buffers) */
void i2s_start(void);

/* Stop I2S output (mute DAC) */
void i2s_stop(void);

/* Push a new audio buffer to the I2S DMA queue
 * Returns 0 on success, -1 if no free DMA slot available */
int i2s_push_buffer(const int16_t *samples, int num_frames);

/* Check if a DMA buffer slot is free for writing */
bool i2s_buffer_available(void);

/* Set I2S output volume (0–100 percent) */
void i2s_set_volume(uint8_t percent);

/* Mute/unmute the DAC output */
void i2s_mute(bool mute);

#endif /* I2S_AUDIO_H */