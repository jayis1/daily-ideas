/*
 * lang_model.h — Character-level n-gram language model API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef LANG_MODEL_H
#define LANG_MODEL_H

#include "esp_err.h"

/**
 * @brief Initialize language model (load bigram table from flash).
 */
esp_err_t lang_model_init(void);

/**
 * @brief Correct a CNN prediction using language model context.
 *
 * @param char_id     CNN predicted character index (0-61)
 * @param confidence  CNN prediction confidence (0.0-1.0)
 * @return Corrected character (ASCII)
 */
char lang_model_correct(int char_id, float confidence);

/**
 * @brief Update language model context with a confirmed character.
 */
void lang_model_update_context(char c);

/**
 * @brief Reset language model context (e.g., after mode switch).
 */
void lang_model_reset_context(void);

#endif /* LANG_MODEL_H */