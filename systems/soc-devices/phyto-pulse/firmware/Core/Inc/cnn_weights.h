/*
 * cnn_weights.h — Quantized int8 CNN weights for spike classification
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Architecture:
 *   Input: 64 × 1 (int8)
 *   Conv1D(8, k=7, s=2, ReLU)  → (29, 8)    [weights: 7×1×8 = 56, bias: 8]
 *   Conv1D(16, k=5, s=1, ReLU) → (25, 16)   [weights: 5×8×16 = 640, bias: 16]
 *   MaxPool1D(2)               → (12, 16)
 *   Conv1D(16, k=3, s=1, ReLU) → (10, 16)   [weights: 3×16×16 = 768, bias: 16]
 *   Flatten                    → 160
 *   Dense(32, ReLU)             → 32        [weights: 160×32 = 5120, bias: 32]
 *   Dense(3, softmax)           → 3         [weights: 32×3 = 96, bias: 3]
 *
 * Total: ~6,700 int8 params ≈ 6.5 KB
 *
 * In a real deployment these would be trained and quantized via
 * TensorFlow Lite for Microcontrollers (TFLM) or STM32 X-CUBE-AI.
 * Here we provide the architecture scaffolding + placeholder weights.
 */

#ifndef CNN_WEIGHTS_H
#define CNN_WEIGHTS_H

#include <stdint.h>

/* Layer dimensions */
#define CONV1_OUT_CH    8
#define CONV1_KERN      7
#define CONV1_STRIDE    2
#define CONV1_OUT_LEN   29   /* (64 - 7) / 2 + 1 */

#define CONV2_OUT_CH    16
#define CONV2_KERN      5
#define CONV2_STRIDE    1
#define CONV2_OUT_LEN   25   /* 29 - 5 + 1 */

#define POOL_STRIDE     2
#define POOL_OUT_LEN    12   /* 25 / 2 */

#define CONV3_OUT_CH    16
#define CONV3_KERN      3
#define CONV3_STRIDE    1
#define CONV3_OUT_LEN   10   /* 12 - 3 + 1 */

#define FLATTEN_LEN     160  /* 10 × 16 */
#define DENSE1_OUT      32
#define DENSE2_OUT      3    /* NUM_CLASSES */

/* Input quantization: scale and zero-point */
#define INPUT_SCALE     0.015625f   /* 1/64, maps ±2V → ±128 */
#define INPUT_ZERO_PT   0

/* Output quantization */
#define OUTPUT_SCALE    0.00390625f  /* 1/256 */
#define OUTPUT_ZERO_PT  0

/* ---- Placeholder weights ----
 * In production, these arrays are filled by TFLM converter output.
 * Placeholder: all-zero weights (network will output uniform softmax).
 * Replace with trained values from the training script. */

/* Conv1: 7×1×8 weights + 8 bias */
static const int8_t conv1_w[CONV1_KERN * CONV1_OUT_CH] = {
    /* [7×8] — flattened kernel: output_ch × kern_len */
    /* Trained values would go here; placeholder zeros for template */
    0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
};
static const int32_t conv1_b[CONV1_OUT_CH] = {0,0,0,0,0,0,0,0};

/* Conv2: 5×8×16 weights + 16 bias */
static const int8_t conv2_w[CONV2_KERN * CONV1_OUT_CH * CONV2_OUT_CH] = {0};
static const int32_t conv2_b[CONV2_OUT_CH] = {0};

/* Conv3: 3×16×16 weights + 16 bias */
static const int8_t conv3_w[CONV3_KERN * CONV2_OUT_CH * CONV3_OUT_CH] = {0};
static const int32_t conv3_b[CONV3_OUT_CH] = {0};

/* Dense1: 160×32 weights + 32 bias */
static const int8_t dense1_w[FLATTEN_LEN * DENSE1_OUT] = {0};
static const int32_t dense1_b[DENSE1_OUT] = {0};

/* Dense2: 32×3 weights + 3 bias */
static const int8_t dense2_w[DENSE1_OUT * DENSE2_OUT] = {0};
static const int32_t dense2_b[DENSE2_OUT] = {0};

/* ReLU activation in quantized domain (int8) */
static inline int8_t relu_int8(int8_t x) {
    return (x > 0) ? x : 0;
}

/* Int8 Conv1D (no padding, stride, with bias + ReLU) */
static void conv1d_int8(const int8_t *input, int input_len,
                        const int8_t *weights, const int32_t *bias,
                        int out_ch, int in_ch, int kern, int stride,
                        int8_t *output, int *out_len)
{
    *out_len = (input_len - kern) / stride + 1;
    for (int oc = 0; oc < out_ch; oc++) {
        for (int pos = 0; pos < *out_len; pos++) {
            int32_t acc = bias[oc];
            for (int ic = 0; ic < in_ch; ic++) {
                for (int k = 0; k < kern; k++) {
                    int idx = pos * stride + k;
                    if (idx < input_len) {
                        acc += (int32_t)input[idx * in_ch + ic] *
                               weights[oc * kern * in_ch + ic * kern + k];
                    }
                }
            }
            /* Scale and ReLU (requantize to int8) */
            acc = acc >> 8;  /* simple shift requantization */
            if (acc > 127) acc = 127;
            if (acc < 0) acc = 0;  /* ReLU */
            output[pos * out_ch + oc] = (int8_t)acc;
        }
    }
}

/* MaxPool1D */
static void maxpool1d_int8(const int8_t *input, int len, int ch,
                           int pool_size, int stride,
                           int8_t *output, int *out_len)
{
    *out_len = (len - pool_size) / stride + 1;
    for (int pos = 0; pos < *out_len; pos++) {
        for (int c = 0; c < ch; c++) {
            int8_t max = -128;
            for (int k = 0; k < pool_size; k++) {
                int idx = pos * stride + k;
                if (idx < len) {
                    int8_t v = input[idx * ch + c];
                    if (v > max) max = v;
                }
            }
            output[pos * ch + c] = max;
        }
    }
}

/* Dense layer with ReLU */
static void dense_int8(const int8_t *input, int in_len,
                       const int8_t *weights, const int32_t *bias,
                       int out_len, int8_t *output, bool use_relu)
{
    for (int o = 0; o < out_len; o++) {
        int32_t acc = bias[o];
        for (int i = 0; i < in_len; i++) {
            acc += (int32_t)input[i] * weights[o * in_len + i];
        }
        acc = acc >> 8;
        if (use_relu && acc < 0) acc = 0;
        if (acc > 127) acc = 127;
        if (acc < -128) acc = -128;
        output[o] = (int8_t)acc;
    }
}

/* Softmax (on int32 logits → float probabilities) */
static void softmax_int32(const int32_t *logits, float *probs, int n)
{
    float max = (float)logits[0];
    for (int i = 1; i < n; i++)
        if ((float)logits[i] > max) max = (float)logits[i];

    float sum = 0;
    for (int i = 0; i < n; i++) {
        probs[i] = expf((float)logits[i] - max);
        sum += probs[i];
    }
    for (int i = 0; i < n; i++) {
        probs[i] /= sum;
    }
}

#endif /* CNN_WEIGHTS_H */