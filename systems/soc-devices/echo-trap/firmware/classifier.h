/*
 * classifier.h — int8 1D-CNN wingbeat species classifier
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */
#ifndef ECHO_TRAP_CLASSIFIER_H
#define ECHO_TRAP_CLASSIFIER_H

#include "i2s_capture.h"

void classifier_init(void);
void classifier_inference(const audio_frame_t *frame,
                          uint8_t *species_id,
                          float *confidence,
                          float *wingbeat_hz);

#endif /* ECHO_TRAP_CLASSIFIER_H */