/*
 * i2s_capture.h — Dual-channel I2S MEMS microphone capture
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_I2S_CAPTURE_H
#define ECHO_TRAP_I2S_CAPTURE_H

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

typedef struct {
    int16_t    mic1[WINDOW_SAMPLES];   /* 4000 samples from ICS-43434 #1 */
    int16_t    mic2[WINDOW_SAMPLES];   /* 4000 samples from ICS-43434 #2 */
    uint64_t   timestamp_us;            /* esp_timer_get_time() at frame start */
} audio_frame_t;

void i2s_capture_init(void);
BaseType_t i2s_capture_get_frame(audio_frame_t *frame, TickType_t timeout);

#endif /* ECHO_TRAP_I2S_CAPTURE_H */