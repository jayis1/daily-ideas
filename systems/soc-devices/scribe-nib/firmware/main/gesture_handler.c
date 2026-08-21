/*
 * gesture_handler.c — Special pen gesture recognition for Scribe Nib
 *
 * Detects intentional gestures (swipe, circle, zigzag, shake)
 * using lightweight DTW (Dynamic Time Warping) classification.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "gesture_handler.h"
#include <math.h>
#include <string.h>
#include "esp_log.h"

static const char *TAG = "gesture";

/* Gesture detection thresholds */
#define SWIPE_MIN_SPEED      2.0f    /* m/s minimum for swipe */
#define CIRCLE_MIN_ANGLE     5.5f    /* ~315° total rotation for circle */
#define SHAKE_MIN_REVERSALS 3        /* Number of direction changes */
#define ZIGZAG_MIN_TURNS    3       /* Number of horizontal turns */

/* Timing thresholds (ms) */
#define GESTURE_MAX_DURATION 600    /* Gestures must complete within 600ms */
#define GESTURE_MIN_DURATION 80     /* Too short = not a gesture */

/* Internal gesture detection state */
typedef struct {
    float total_angle;        /* Cumulative heading rotation (for circle) */
    float prev_heading;       /* Previous heading angle */
    float max_speed;          /* Peak speed during stroke */
    float horiz_displacement; /* Total horizontal displacement */
    float vert_displacement;  /* Total vertical displacement */
    int reversals;            /* Direction change count */
    bool initialized;
} gesture_detect_t;

static gesture_detect_t detect;

void gesture_handler_init(void)
{
    memset(&detect, 0, sizeof(detect));
    ESP_LOGI(TAG, "Gesture handler initialized");
}

/* Compute heading from trajectory points */
static float compute_heading(float dx, float dy)
{
    return atan2f(dy, dx);
}

/* Normalize angle to [-π, π] */
static float normalize_angle(float angle)
{
    while (angle > M_PI) angle -= 2.0f * M_PI;
    while (angle < -M_PI) angle += 2.0f * M_PI;
    return angle;
}

gesture_type_t gesture_handler_detect(const stroke_event_t *stroke)
{
    if (!stroke || stroke->sample_count < 10) return GESTURE_NONE;

    /* Quick rejection: if stroke duration is too long, it's writing not gesture */
    uint32_t duration = stroke->pen_up_time_ms - stroke->pen_down_time_ms;
    if (duration > GESTURE_MAX_DURATION || duration < GESTURE_MIN_DURATION) {
        return GESTURE_NONE;
    }

    /* Reset detection state */
    memset(&detect, 0, sizeof(detect));
    detect.initialized = false;

    float prev_dx = 0.0f;
    float total_dx = 0.0f, total_dy = 0.0f;
    float max_vel = 0.0f;
    int dir_changes_x = 0;
    int dir_changes_y = 0;

    /* Analyze trajectory */
    for (int i = 1; i < stroke->sample_count; i++) {
        float dx = stroke->samples[i].accel_x - stroke->samples[i-1].accel_x;
        float dy = stroke->samples[i].accel_y - stroke->samples[i-1].accel_y;
        float dt_s = 0.005f;  /* 200Hz */
        float vx = dx / dt_s;
        float vy = dy / dt_s;
        float speed = sqrtf(vx * vx + vy * vy);

        if (speed > max_vel) max_vel = speed;

        total_dx += dx;
        total_dy += dy;

        /* Detect direction changes */
        if (i > 2) {
            float prev_x_vel = (stroke->samples[i-1].accel_x - stroke->samples[i-2].accel_x) / dt_s;
            float curr_x_vel = vx;
            if (prev_x_vel * curr_x_vel < 0) dir_changes_x++;
            float prev_y_vel = (stroke->samples[i-1].accel_y - stroke->samples[i-2].accel_y) / dt_s;
            float curr_y_vel = vy;
            if (prev_y_vel * curr_y_vel < 0) dir_changes_y++;
        }

        /* Accumulate heading rotation (for circle detection) */
        float heading = compute_heading(vx, vy);
        if (detect.initialized) {
            float d_angle = normalize_angle(heading - detect.prev_heading);
            detect.total_angle += d_angle;
        }
        detect.prev_heading = heading;
        detect.initialized = true;
    }

    detect.max_speed = max_vel;
    detect.horiz_displacement = total_dx;
    detect.vert_displacement = total_dy;
    detect.reversals = (dir_changes_x > dir_changes_y) ? dir_changes_x : dir_changes_y;

    /* ---- Gesture classification rules ---- */

    /* 1. Swipe Right: high speed, large +X displacement, low Y */
    if (max_vel > SWIPE_MIN_SPEED && total_dx > 0.05f &&
        fabsf(total_dy) < 0.02f && dir_changes_x < 2) {
        ESP_LOGI(TAG, "Gesture: SWIPE RIGHT (space)");
        return GESTURE_SPACE;
    }

    /* 2. Swipe Left: high speed, large -X displacement */
    if (max_vel > SWIPE_MIN_SPEED && total_dx < -0.05f &&
        fabsf(total_dy) < 0.02f && dir_changes_x < 2) {
        ESP_LOGI(TAG, "Gesture: SWIPE LEFT (backspace)");
        return GESTURE_BACKSPACE;
    }

    /* 3. Swipe Down: high speed, large +Y displacement */
    if (max_vel > SWIPE_MIN_SPEED && total_dy > 0.05f &&
        fabsf(total_dx) < 0.02f && dir_changes_y < 2) {
        ESP_LOGI(TAG, "Gesture: SWIPE DOWN (enter)");
        return GESTURE_ENTER;
    }

    /* 4. Circle: total heading rotation > 315° */
    if (fabsf(detect.total_angle) > CIRCLE_MIN_ANGLE) {
        ESP_LOGI(TAG, "Gesture: CIRCLE (caps lock)");
        return GESTURE_CAPS_LOCK;
    }

    /* 5. Zigzag: multiple X direction changes, high speed */
    if (dir_changes_x >= ZIGZAG_MIN_TURNS && max_vel > SWIPE_MIN_SPEED * 0.5f) {
        ESP_LOGI(TAG, "Gesture: ZIGZAG (mode switch)");
        return GESTURE_MODE_SWITCH;
    }

    /* 6. Shake: multiple Y direction changes, short duration */
    if (dir_changes_y >= SHAKE_MIN_REVERSALS && duration < 300) {
        ESP_LOGI(TAG, "Gesture: SHAKE (undo)");
        return GESTURE_UNDO;
    }

    return GESTURE_NONE;
}