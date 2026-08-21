/*
 * calibration.h — User handwriting profile calibration API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef CALIBRATION_H
#define CALIBRATION_H

#include "esp_err.h"
#include <stdint.h>

/**
 * @brief Load a calibration profile from NVS (or use defaults).
 * @param profile_id  Profile index (0-3)
 */
esp_err_t calibration_load_profile(uint8_t profile_id);

/**
 * @brief Save current calibration profile to NVS.
 * @param profile_id  Profile index (0-3)
 */
esp_err_t calibration_save_profile(uint8_t profile_id);

/**
 * @brief Update gravity reference from a stationary sample.
 * @param z_accel  Current Z-axis acceleration
 */
esp_err_t calibration_update_gravity(float z_accel);

/**
 * @brief Get current gravity reference value.
 */
float calibration_get_gravity(void);

/**
 * @brief Get trajectory scaling factor.
 */
float calibration_get_stroke_scale(void);

/**
 * @brief Set trajectory scaling factor.
 */
void calibration_set_stroke_scale(float scale);

/**
 * @brief Get active profile index.
 */
uint8_t calibration_get_active_profile(void);

#endif /* CALIBRATION_H */