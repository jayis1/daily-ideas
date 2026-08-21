/*
 * Flux Ring — haptic_feedback.h
 * DRV2603L haptic motor driver + vibration pattern engine.
 */

#ifndef HAPTIC_FEEDBACK_H_
#define HAPTIC_FEEDBACK_H_

#include <zephyr/drivers/i2c.h>
#include <stdint.h>
#include "field_engine.h"

#define DRV2603L_I2C_ADDR   0x5A

/**
 * Initialize DRV2603L haptic driver over I2C.
 */
int haptic_feedback_init(const struct device *i2c_dev);

/**
 * Set haptic intensity and pattern based on field strength and pole.
 * @param magnitude_gauss  Total field magnitude
 * @param pole             Dominant pole (N/S/none)
 */
void haptic_feedback_set_intensity(float magnitude_gauss, pole_t pole);

/**
 * Turn off haptic feedback.
 */
void haptic_feedback_off(void);

/**
 * Single short pulse (for UI feedback).
 * @param duration_ms  Pulse duration in ms
 */
void haptic_pulse(uint32_t duration_ms);

#endif /* HAPTIC_FEEDBACK_H_ */