/*
 * preprocess.h — Acoustic pre-processing: band-pass filter, energy gate,
 *                adaptive noise floor, autocorrelation wingbeat frequency
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_PREPROCESS_H
#define ECHO_TRAP_PREPROCESS_H

#include "i2s_capture.h"

typedef struct {
    float    rms_dbfs;          /* RMS energy in dBFS */
    float    wingbeat_hz;       /* dominant autocorrelation frequency */
    float    noise_floor_dbfs;  /* adaptive noise floor */
    int      has_signal;         /* 1 if energy above threshold */
} preprocess_result_t;

void preprocess_init(void);
int preprocess_frame(const audio_frame_t *frame, preprocess_result_t *result);

#endif /* ECHO_TRAP_PREPROCESS_H */