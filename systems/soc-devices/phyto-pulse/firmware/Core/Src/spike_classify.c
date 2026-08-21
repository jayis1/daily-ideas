/*
 * spike_classify.c — int8 1D-CNN spike classifier
 * Phyto Pulse — Plant Electrophysiology Recorder
 */

#include "spike_classify.h"
#include "cnn_weights.h"
#include "spike_detect.h"
#include <math.h>
#include <string.h>

const char *const CLASS_NAMES[NUM_CLASSES] = { "AP", "VP", "ART" };

/* Working buffers for intermediate activations */
static int8_t  conv1_out[CONV1_OUT_LEN * CONV1_OUT_CH];      /* 29×8 = 232 */
static int8_t  conv2_out[CONV2_OUT_LEN * CONV2_OUT_CH];     /* 25×16 = 400 */
static int8_t  pool_out[POOL_OUT_LEN * CONV2_OUT_CH];       /* 12×16 = 192 */
static int8_t  conv3_out[CONV3_OUT_LEN * CONV3_OUT_CH];     /* 10×16 = 160 */
static int8_t  dense1_out[DENSE1_OUT];                      /* 32 */
static int32_t dense2_logits[DENSE2_OUT];                    /* 3 */

static int8_t g_input_buf[CNN_INPUT_LEN];
static int8_t g_last_window[CNN_INPUT_LEN];

void spike_classify_init(void)
{
    memset(conv1_out, 0, sizeof(conv1_out));
    memset(conv2_out, 0, sizeof(conv2_out));
    memset(pool_out, 0, sizeof(pool_out));
    memset(conv3_out, 0, sizeof(conv3_out));
    memset(dense1_out, 0, sizeof(dense1_out));
    memset(dense2_logits, 0, sizeof(dense2_logits));
    memset(g_input_buf, 0, sizeof(g_input_buf));
    memset(g_last_window, 0, sizeof(g_last_window));
}

static void extract_window(const spike_event_t *event, int8_t *out)
{
    /* Get a window of samples centered on the peak from the ring buffer.
     * Downsample/up-sample to exactly CNN_INPUT_LEN (64) samples.
     * Quantize to int8 using INPUT_SCALE.
     */
    float window[512];  /* max raw samples */
    int n = spike_detect_get_window(window, 512);

    /* Find the peak sample position (approximate using sample_index) */
    int center = n / 2;  /* assume ring buffer is centered around recent */
    if (event->sample_index > 0) {
        /* Try to align: the ring buffer's latest sample is the most recent */
        center = n - (n / 4);  /* peak is near the end for recent events */
    }

    /* Extract 64 samples around the peak with linear resampling */
    int half = CNN_INPUT_LEN / 2;
    int span = 64;  /* ±64 samples around peak = 128 total → resample to 64 */
    int start = center - half;
    if (start < 0) start = 0;
    if (start + CNN_INPUT_LEN > n) {
        start = n - CNN_INPUT_LEN;
        if (start < 0) start = 0;
    }

    /* Resample: pick every other sample (decimate by 2) */
    for (int i = 0; i < CNN_INPUT_LEN; i++) {
        int src = start + i * 2;
        if (src >= n) src = n - 1;
        /* Quantize: int8 = voltage_mV / INPUT_SCALE */
        float q = window[src] / INPUT_SCALE;
        if (q > 127.0f) q = 127.0f;
        if (q < -128.0f) q = -128.0f;
        out[i] = (int8_t)q;
    }
}

int spike_classify_event(spike_event_t *event)
{
    /* 1. Extract 64-sample window from ring buffer */
    extract_window(event, g_input_buf);
    memcpy(g_last_window, g_input_buf, CNN_INPUT_LEN);

    /* 2. Conv1D(8, k=7, s=2, ReLU) */
    int out_len;
    conv1d_int8(g_input_buf, CNN_INPUT_LEN,
                conv1_w, conv1_b,
                CONV1_OUT_CH, 1, CONV1_KERN, CONV1_STRIDE,
                conv1_out, &out_len);

    /* 3. Conv1D(16, k=5, s=1, ReLU) */
    conv1d_int8(conv1_out, CONV1_OUT_LEN,
                conv2_w, conv2_b,
                CONV2_OUT_CH, CONV1_OUT_CH, CONV2_KERN, CONV2_STRIDE,
                conv2_out, &out_len);

    /* 4. MaxPool1D(2) */
    maxpool1d_int8(conv2_out, CONV2_OUT_LEN, CONV2_OUT_CH,
                   2, POOL_STRIDE, pool_out, &out_len);

    /* 5. Conv1D(16, k=3, s=1, ReLU) */
    conv1d_int8(pool_out, POOL_OUT_LEN,
                conv3_w, conv3_b,
                CONV3_OUT_CH, CONV2_OUT_CH, CONV3_KERN, CONV3_STRIDE,
                conv3_out, &out_len);

    /* 6. Dense(32, ReLU) — flatten conv3_out (10×16 = 160) */
    dense_int8(conv3_out, FLATTEN_LEN,
               dense1_w, dense1_b,
               DENSE1_OUT, dense1_out, true);

    /* 7. Dense(3) — output logits (int32, no requantization for softmax) */
    for (int o = 0; o < DENSE2_OUT; o++) {
        int32_t acc = dense2_b[o];
        for (int i = 0; i < DENSE1_OUT; i++) {
            acc += (int32_t)dense1_out[i] * dense2_w[o * DENSE1_OUT + i];
        }
        dense2_logits[o] = acc;
    }

    /* 8. Softmax → probabilities */
    float probs[NUM_CLASSES];
    softmax_int32(dense2_logits, probs, NUM_CLASSES);

    /* 9. Argmax + confidence */
    int best = 0;
    for (int i = 1; i < NUM_CLASSES; i++) {
        if (probs[i] > probs[best]) best = i;
    }
    event->confidence = probs[best];
    event->classification = (event_type_t)best;

    return best;
}

void spike_classify_get_last_window(int8_t *buffer, int *actual_len)
{
    memcpy(buffer, g_last_window, CNN_INPUT_LEN);
    *actual_len = CNN_INPUT_LEN;
}