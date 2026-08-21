/*
 * audio.h — I2S driver (ESP32-S3 → PCM5102A)
 */
#pragma once
#include <stdint.h>
#include <stddef.h>

void audio_init(void);
void audio_write_block(const int16_t *data, size_t bytes);