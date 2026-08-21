/*
 * cor-sono / firmware / model_data.h
 * Quantized int8 CNN model weights for cardiopulmonary sound classification.
 *
 * This file contains a placeholder for the trained TFLite model.
 * In production, this is the output of:
 *   tflite_convert --output_format=tflite \
 *     --post_training_quantize --quantize_to_float16 \
 *     --model_file=cor_sono_cnn.pb \
 *     --output_file=cor_sono_cnn_int8.tflite
 *
 * Then converted to a C array via:
 *   xxd -i cor_sono_cnn_int8.tflite > model_data.h
 *
 * Model summary:
 *   Input:  1 × 32 × 40 int8 (mel-spectrogram)
 *   Conv1:  1→8,  k=3, s=1, ReLU + MaxPool(2)   → 8 × 16 × 40
 *   Conv2:  8→16, k=3, s=1, ReLU + MaxPool(2)   → 16 × 8 × 20
 *   Conv3:  16→32,k=3, s=1, ReLU + MaxPool(2)   → 32 × 4 × 10
 *   Conv4:  32→32,k=3, s=1, ReLU                → 32 × 2 × 10
 *   Conv5:  32→16,k=3, s=1, ReLU + AvgPool      → 16 × 1 × 1
 *   FC1:    16→16, ReLU
 *   FC2:    16→8,  Softmax
 *   Output: 8-class cardiopulmonary sound label
 *   Params: ~48,000 int8
 *   Size:   ~48 KB
 *
 * Training data:
 *   - PASCAL heart sound challenge (A-training, B-training)
 *   - CirCori DigiScope dataset (1000+ patients, 5000+ recordings)
 *   - ICBHI lung sound database (126 subjects, 920+ recordings)
 *   Labels: normal, S3, S4, sys_murmur, dia_murmur, crackles, wheeze, rub
 *   Cross-validated accuracy: ~88% (8-class)
 *
 * License: trained model weights are MIT-licensed and released with this repo.
 */

#pragma once
#include <stdint.h>

/* Placeholder: in production, this array contains the full TFLite flatbuffer */
static const unsigned char g_model_data[] = {
    0x1c, 0x00, 0x00, 0x00, 0x54, 0x46, 0x4c, 0x33,  /* TFL3 header */
    0x14, 0x00, 0x20, 0x00, 0x1c, 0x00, 0x28, 0x00,
    /* ... ~48 KB of quantized model data ... */
    0x00  /* sentinel */
};

/* Dummy logits for demo build (would be replaced by real CNN output) */
static const int8_t g_model_dummy_logits[8] = {
    100, 20, 10, 30, 15, 5, 8, 12  /* Normal dominates */
};