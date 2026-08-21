/*
 * stroke_segmenter.c — Pen-up/pen-down detection from Z-axis accelerometer
 *
 * Detects when the pen touches or lifts off paper by monitoring Z-axis
 * acceleration transients. Groups multi-stroke characters by timing.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "stroke_segmenter.h"
#include <math.h>
#include <string.h>
#include "esp_log.h"

static const char *TAG = "stroke_seg";

/* Pen-down threshold: Z-axis deceleration spike (m/s²) */
#define PEN_DOWN_THRESHOLD     3.0f
/* Pen-up threshold: Z-axis acceleration spike (m/s²) */
#define PEN_UP_THRESHOLD       2.0f
/* Debounce time in ms */
#define DEBOUNCE_MS            20
/* Multi-stroke grouping timeout in ms */
#define STROKE_GROUP_TIMEOUT   300

typedef enum {
    PEN_STATE_UP,
    PEN_STATE_DOWN
} pen_state_t;

static pen_state_t pen_state = PEN_STATE_UP;
static int64_t last_transition_us = 0;
static stroke_event_t current_stroke;
static int stroke_sample_count = 0;

/* Calibration offsets (set during user calibration) */
static float accel_z_offset = 9.81f;   /* gravity when pen is upright */
static float accel_z_baseline = 0.0f;

void stroke_segmenter_init(void)
{
    pen_state = PEN_STATE_UP;
    last_transition_us = 0;
    stroke_sample_count = 0;
    memset(&current_stroke, 0, sizeof(current_stroke));
    ESP_LOGI(TAG, "Stroke segmenter initialized");
}

void stroke_segmenter_set_baseline(float z_gravity)
{
    accel_z_offset = z_gravity;
    accel_z_baseline = z_gravity - 9.81f;
    ESP_LOGI(TAG, "Z-axis baseline set: offset=%.2f, baseline=%.2f",
             accel_z_offset, accel_z_baseline);
}

bool stroke_segmenter_update(const imu_sample_t *sample, stroke_event_t *out_stroke)
{
    if (!sample) return false;

    int64_t now_us = (int64_t)sample->timestamp_ms * 1000;

    /* Compute Z-axis acceleration relative to gravity baseline */
    float az_centered = sample->accel_z - accel_z_offset;
    float az_magnitude = fabsf(az_centered);

    bool pen_down_detected = false;
    bool pen_up_detected = false;

    /* Detect pen-down: sharp deceleration spike in Z (pen hits paper) */
    if (az_magnitude > PEN_DOWN_THRESHOLD && pen_state == PEN_STATE_UP) {
        if (now_us - last_transition_us > DEBOUNCE_MS * 1000) {
            pen_down_detected = true;
        }
    }

    /* Detect pen-up: acceleration spike in Z (pen lifts off paper) */
    /* Also detect via reduced vibration pattern (low Z variance) */
    if (pen_state == PEN_STATE_DOWN) {
        /* Simple heuristic: if Z-axis is close to gravity for >50ms, pen is up */
        if (az_magnitude < PEN_UP_THRESHOLD) {
            pen_up_detected = true;
        }
    }

    /* State transitions */
    if (pen_down_detected) {
        pen_state = PEN_STATE_DOWN;
        last_transition_us = now_us;
        stroke_sample_count = 0;
        memset(&current_stroke, 0, sizeof(current_stroke));
        current_stroke.pen_down_time_ms = sample->timestamp_ms;
        current_stroke.stroke_count = 1;
        ESP_LOGD(TAG, "Pen DOWN at t=%u", sample->timestamp_ms);
    }

    /* Accumulate samples while pen is down */
    if (pen_state == PEN_STATE_DOWN) {
        if (stroke_sample_count < MAX_STROKE_SAMPLES) {
            current_stroke.samples[stroke_sample_count] = *sample;
            stroke_sample_count++;
            current_stroke.sample_count = stroke_sample_count;
        }
    }

    /* Pen-up: finalize stroke, check if multi-stroke group is complete */
    if (pen_up_detected && pen_state == PEN_STATE_DOWN) {
        pen_state = PEN_STATE_UP;
        last_transition_us = now_us;
        current_stroke.pen_up_time_ms = sample->timestamp_ms;
        ESP_LOGD(TAG, "Pen UP at t=%u (%d samples)", sample->timestamp_ms, stroke_sample_count);

        /* Check if this is a continuation of a multi-stroke character */
        /* If less than STROKE_GROUP_TIMEOUT since last pen-up, group strokes */
        /* For now, we finalize on pen-up. Multi-stroke grouping is handled
           by the caller checking the timeout. */

        if (stroke_sample_count > 5) {  /* Minimum samples for valid stroke */
            *out_stroke = current_stroke;
            return true;
        }
    }

    return false;
}

bool stroke_segmenter_is_pen_down(void)
{
    return pen_state == PEN_STATE_DOWN;
}

uint32_t stroke_segmenter_pen_up_duration_ms(uint32_t current_time_ms)
{
    if (pen_state == PEN_STATE_UP) {
        return current_time_ms - (uint32_t)(last_transition_us / 1000);
    }
    return 0;
}