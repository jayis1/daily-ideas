/*
 * Ping Caliper — Handheld Ultrasonic NDT Gauge
 * STM32G474RET6 Firmware
 *
 * calibration.h — Zero-probe (delay-line) and velocity calibration
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef CALIBRATION_H
#define CALIBRATION_H

#include "config.h"
#include "receiver.h"

typedef enum {
    CAL_STATE_IDLE = 0,
    CAL_STATE_ZERO_PROBE,
    CAL_STATE_VELOCITY,
    CAL_STATE_GAIN,
    CAL_STATE_DONE,
    CAL_STATE_FAILED,
} cal_state_t;

typedef struct {
    cal_state_t state;
    uint16_t     zero_offset_ns;   /* probe delay-line zero offset          */
    uint32_t     measured_velocity_mps;
    float        reference_thickness_mm;  /* known block thickness for vel cal */
    float        gain_offset_db;    /* receiver gain offset                */
} calibration_t;

void calibration_init(void);
void calibration_start_zero(void);
void calibration_start_velocity(float known_thickness_mm);
void calibration_update(const ascan_t *scan, calibration_t *cal);

/* Persist calibration to flash (nonvolatile). */
void calibration_save(const calibration_t *cal);
void calibration_load(calibration_t *cal);

/* Retrieve current active calibration. */
const calibration_t *calibration_get(void);

#endif /* CALIBRATION_H */