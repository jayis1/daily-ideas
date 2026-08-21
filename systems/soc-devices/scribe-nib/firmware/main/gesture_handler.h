/*
 * gesture_handler.h — Special pen gesture recognition API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef GESTURE_HANDLER_H
#define GESTURE_HANDLER_H

#include "stroke_segmenter.h"

typedef enum {
    GESTURE_NONE       = 0,
    GESTURE_SPACE      = 1,  /* Swipe right */
    GESTURE_BACKSPACE  = 2,  /* Swipe left */
    GESTURE_ENTER     = 3,  /* Swipe down */
    GESTURE_CAPS_LOCK = 4,  /* Circle */
    GESTURE_MODE_SWITCH = 5,/* Zigzag */
    GESTURE_UNDO       = 6, /* Shake */
} gesture_type_t;

/**
 * @brief Initialize gesture handler.
 */
void gesture_handler_init(void);

/**
 * @brief Detect gesture from a completed stroke event.
 *
 * @param stroke  Completed stroke event
 * @return Detected gesture type (GESTURE_NONE if not a gesture)
 */
gesture_type_t gesture_handler_detect(const stroke_event_t *stroke);

#endif /* GESTURE_HANDLER_H */