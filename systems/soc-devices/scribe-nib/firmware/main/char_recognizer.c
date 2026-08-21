/*
 * char_recognizer.c — On-device CNN character recognition for Scribe Nib
 *
 * Uses TFLite Micro to run a 62-class INT8 quantized CNN on rendered
 * 32×32 trajectory images. Supports mode switching and caps lock.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "char_recognizer.h"
#include <string.h>
#include "esp_log.h"
#include "esp_system.h"

/* TFLite Micro includes */
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

static const char *TAG = "char_recog";

/* Character set: 0-9, A-Z, a-z */
static const char charset[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
#define NUM_CLASSES 62

/* CNN model data (linked from flash partition) */
extern const unsigned char char_cnn_model_tflite[];
extern const unsigned int char_cnn_model_tflite_len;

/* TFLite Micro interpreter resources */
static const tflite::Model *model = nullptr;
static tflite::MicroMutableOpResolver<8> *op_resolver = nullptr;
static tflite::MicroInterpreter *interpreter = nullptr;

/* Tensor arena for TFLite Micro (64KB should be plenty for this tiny model) */
static constexpr int kTensorArenaSize = 65536;
static uint8_t tensor_arena[kTensorArenaSize] __attribute__((aligned(16)));

/* Rendering buffer: 32×32 grayscale image */
#define RENDER_SIZE 32
static uint8_t render_buf[RENDER_SIZE * RENDER_SIZE];

/* Recognition mode */
static recog_mode_t current_mode = RECOG_MODE_AUTO;
static bool caps_lock = false;

/* ---- Rendering: trajectory → 32×32 grayscale image ---- */

static void render_trajectory(const traj_2d_t *traj)
{
    /* Clear buffer */
    memset(render_buf, 0, sizeof(render_buf));

    if (traj->point_count < 2) return;

    /* Render with Bresenham line algorithm, pen width ~1.5px */
    for (int i = 0; i < traj->point_count - 1; i++) {
        float x0f = traj->points[i].x * (RENDER_SIZE - 4) + 2;  /* 2px margin */
        float y0f = traj->points[i].y * (RENDER_SIZE - 4) + 2;
        float x1f = traj->points[i + 1].x * (RENDER_SIZE - 4) + 2;
        float y1f = traj->points[i + 1].y * (RENDER_SIZE - 4) + 2;

        int x0 = (int)x0f, y0 = (int)y0f;
        int x1 = (int)x1f, y1 = (int)y1f;

        /* Bresenham line */
        int dx = abs(x1 - x0);
        int dy = -abs(y1 - y0);
        int sx = x0 < x1 ? 1 : -1;
        int sy = y0 < y1 ? 1 : -1;
        int err = dx + dy;

        while (1) {
            /* Plot pixel with ~1.5px pen width (plot center + neighbors) */
            for (int py = -1; py <= 1; py++) {
                for (int px = -1; px <= 1; px++) {
                    int px_x = x0 + px;
                    int px_y = y0 + py;
                    if (px_x >= 0 && px_x < RENDER_SIZE && px_y >= 0 && px_y < RENDER_SIZE) {
                        /* Distance-weighted intensity for anti-aliasing */
                        float dist = sqrtf((float)(px * px + py * py));
                        uint8_t intensity = (dist < 0.8f) ? 255 :
                                           (dist < 1.3f) ? 192 :
                                           (dist < 1.8f) ? 96 : 0;
                        int idx = px_y * RENDER_SIZE + px_x;
                        if (intensity > render_buf[idx]) {
                            render_buf[idx] = intensity;
                        }
                    }
                }
            }

            if (x0 == x1 && y0 == y1) break;
            int e2 = 2 * err;
            if (e2 >= dy) { err += dy; x0 += sx; }
            if (e2 <= dx) { err += dx; y0 += sy; }
        }
    }

    /* Apply simple Gaussian-like blur for anti-aliasing (3×3 averaging) */
    uint8_t blur_buf[RENDER_SIZE * RENDER_SIZE];
    memcpy(blur_buf, render_buf, sizeof(blur_buf));

    for (int y = 1; y < RENDER_SIZE - 1; y++) {
        for (int x = 1; x < RENDER_SIZE - 1; x++) {
            int sum = 0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    sum += blur_buf[(y + ky) * RENDER_SIZE + (x + kx)];
                }
            }
            render_buf[y * RENDER_SIZE + x] = (uint8_t)(sum / 9);
        }
    }
}

/* ---- Public API ---- */

esp_err_t char_recognizer_init(void)
{
    /* Load model from flash */
    model = tflite::GetModel(char_cnn_model_tflite);
    if (!model) {
        ESP_LOGE(TAG, "Failed to load TFLite model");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "Model loaded: %d bytes", char_cnn_model_tflite_len);

    /* Set up operation resolver for the CNN layers */
    op_resolver = new tflite::MicroMutableOpResolver<8>();
    op_resolver->AddConv2D();
    op_resolver->AddDepthwiseConv2D();
    op_resolver->AddFullyConnected();
    op_resolver->AddReshape();
    op_resolver->AddSoftmax();
    op_resolver->AddAveragePool2D();
    op_resolver->AddRelu();
    op_resolver->AddQuantize();

    /* Create interpreter */
    interpreter = new tflite::MicroInterpreter(
        model, *op_resolver, tensor_arena, kTensorArenaSize);

    /* Allocate tensors */
    if (interpreter->AllocateTensors() != kTfLiteOk) {
        ESP_LOGE(TAG, "AllocateTensors() failed");
        return ESP_FAIL;
    }

    ESP_LOGI(TAG, "Character recognizer initialized (62-class CNN)");

    return ESP_OK;
}

char_pred_t char_recognizer_classify(const traj_2d_t *traj)
{
    char_pred_t result = { -1, 0.0f };

    if (!interpreter || !traj) return result;

    /* Render trajectory to 32×32 image */
    render_trajectory(traj);

    /* Get input tensor and fill with rendered image */
    TfLiteTensor *input = interpreter->input(0);
    if (!input) {
        ESP_LOGE(TAG, "No input tensor");
        return result;
    }

    /* Model expects INT8 input, so convert from uint8 */
    int8_t *input_data = interpreter->typed_input_tensor<int8_t>(0);
    for (int i = 0; i < RENDER_SIZE * RENDER_SIZE; i++) {
        /* Convert uint8 [0..255] to int8 [-128..127] */
        input_data[i] = (int8_t)((int)render_buf[i] - 128);
    }

    /* Run inference */
    if (interpreter->Invoke() != kTfLiteOk) {
        ESP_LOGE(TAG, "Invoke() failed");
        return result;
    }

    /* Get output tensor (62-class softmax, INT8) */
    const TfLiteTensor *output = interpreter->output(0);
    const int8_t *output_data = interpreter->typed_output_tensor<int8_t>(0);

    /* Find class with maximum probability */
    int max_idx = 0;
    int8_t max_val = output_data[0];
    for (int i = 1; i < NUM_CLASSES; i++) {
        if (output_data[i] > max_val) {
            max_val = output_data[i];
            max_idx = i;
        }
    }

    /* Convert INT8 confidence to float (approximate softmax) */
    float confidence = (float)(max_val + 128) / 255.0f;

    /* Apply mode filtering */
    int char_id = max_idx;
    if (current_mode == RECOG_MODE_LETTERS) {
        /* Only allow A-Z (indices 10-35) and a-z (indices 36-61) */
        if (char_id < 10) {
            /* Digit detected in letter mode — check second-best */
            int8_t second_val = -128;
            int second_idx = 0;
            for (int i = 10; i < NUM_CLASSES; i++) {
                if (output_data[i] > second_val) {
                    second_val = output_data[i];
                    second_idx = i;
                }
            }
            char_id = second_idx;
            confidence = (float)(second_val + 128) / 255.0f;
        }
    } else if (current_mode == RECOG_MODE_NUMBERS) {
        /* Only allow 0-9 (indices 0-9) */
        if (char_id >= 10) {
            int8_t second_val = -128;
            int second_idx = 0;
            for (int i = 0; i < 10; i++) {
                if (output_data[i] > second_val) {
                    second_val = output_data[i];
                    second_idx = i;
                }
            }
            char_id = second_idx;
            confidence = (float)(second_val + 128) / 255.0f;
        }
    }

    /* Apply caps lock */
    if (caps_lock && char_id >= 36) {
        /* lowercase → uppercase */
        char_id = char_id - 26;
    }

    result.char_id = char_id;
    result.confidence = confidence;

    return result;
}

void char_recognizer_toggle_caps(void)
{
    caps_lock = !caps_lock;
    ESP_LOGI(TAG, "Caps lock: %s", caps_lock ? "ON" : "OFF");
}

void char_recognizer_toggle_mode(void)
{
    current_mode = (recog_mode_t)((current_mode + 1) % 3);
    const char *mode_names[] = {"AUTO", "LETTERS", "NUMBERS"};
    ESP_LOGI(TAG, "Recognition mode: %s", mode_names[current_mode]);
}

recog_mode_t char_recognizer_get_mode(void)
{
    return current_mode;
}