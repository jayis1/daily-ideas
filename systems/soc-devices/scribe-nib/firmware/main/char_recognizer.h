/*
 * char_recognizer.h — On-device CNN character recognition API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef CHAR_RECOGNIZER_H
#define CHAR_RECOGNIZER_H

#include "esp_err.h"
#include "trajectory_recon.h"

#define NUM_CHAR_CLASSES 62

/* Recognition mode */
typedef enum {
    RECOG_MODE_AUTO    = 0,  /* Accept any class */
    RECOG_MODE_LETTERS = 1,  /* Only A-Z / a-z */
    RECOG_MODE_NUMBERS = 2,  /* Only 0-9 */
} recog_mode_t;

/* Recognition result */
typedef struct {
    int char_id;        /* 0-9=digits, 10-35=uppercase, 36-61=lowercase */
    float confidence;   /* 0.0 to 1.0 */
} char_pred_t;

/**
 * @brief Initialize character recognizer (loads CNN model from flash).
 */
esp_err_t char_recognizer_init(void);

/**
 * @brief Classify a 2D trajectory into a character.
 *
 * @param traj  2D trajectory (normalized 0.0-1.0)
 * @return Prediction result with char_id and confidence
 */
char_pred_t char_recognizer_classify(const traj_2d_t *traj);

/**
 * @brief Toggle caps lock state.
 */
void char_recognizer_toggle_caps(void);

/**
 * @brief Toggle recognition mode (auto/letters/numbers).
 */
void char_recognizer_toggle_mode(void);

/**
 * @brief Get current recognition mode.
 */
recog_mode_t char_recognizer_get_mode(void);

#endif /* CHAR_RECOGNIZER_H */