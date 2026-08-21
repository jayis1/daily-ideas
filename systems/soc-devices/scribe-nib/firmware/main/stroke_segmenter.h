/*
 * stroke_segmenter.h — Pen-up/pen-down stroke segmentation API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef STROKE_SEGMENTER_H
#define STROKE_SEGMENTER_H

#include <stdbool.h>
#include <stdint.h>
#include "imu_driver.h"

#define MAX_STROKE_SAMPLES  512

/* A complete stroke event: from pen-down to pen-up */
typedef struct {
    imu_sample_t samples[MAX_STROKE_SAMPLES];
    int sample_count;
    uint32_t pen_down_time_ms;
    uint32_t pen_up_time_ms;
    int stroke_count;     /* 1 for single, >1 for multi-stroke */
} stroke_event_t;

/**
 * @brief Initialize the stroke segmenter.
 */
void stroke_segmenter_init(void);

/**
 * @brief Set the Z-axis gravity baseline for pen-up/pen-down detection.
 *
 * @param z_gravity  Measured Z-axis value when pen is upright and still
 */
void stroke_segmenter_set_baseline(float z_gravity);

/**
 * @brief Feed a new IMU sample to the segmenter.
 *
 * @param sample      Latest IMU sample
 * @param out_stroke  Output stroke event (valid only when returns true)
 * @return true if a complete stroke was detected, false otherwise
 */
bool stroke_segmenter_update(const imu_sample_t *sample, stroke_event_t *out_stroke);

/**
 * @brief Check if pen is currently down (writing).
 */
bool stroke_segmenter_is_pen_down(void);

/**
 * @brief Get time since last pen-up (for multi-stroke grouping).
 */
uint32_t stroke_segmenter_pen_up_duration_ms(uint32_t current_time_ms);

#endif /* STROKE_SEGMENTER_H */