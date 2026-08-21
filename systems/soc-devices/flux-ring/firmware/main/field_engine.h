/*
 * Flux Ring — field_engine.h
 * Tilt-compensated magnetic field processing engine.
 */

#ifndef FIELD_ENGINE_H_
#define FIELD_ENGINE_H_

#include "mag_sensor.h"
#include "accel_sensor.h"
#include <math.h>

/* Tilt-compensated magnetic field vector */
typedef struct {
    float x, y, z;          /* Gauss, tilt-compensated */
    float x_raw, y_raw, z_raw; /* Raw (before tilt compensation) */
} field_vector_t;

/* Pole classification */
typedef enum {
    POLE_NONE = 0,   /* Symmetric / ambient */
    POLE_N    = 1,   /* North pole dominant (field lines toward sensor) */
    POLE_S    = 2    /* South pole dominant (field lines away from sensor) */
} pole_t;

/**
 * Perform tilt compensation on magnetic field vector using accelerometer.
 * Projects magnetic vector onto horizontal plane using roll/pitch from gravity.
 */
field_vector_t field_engine_compensate(const mag_data_t *mag,
                                       const accel_data_t *accel);

/**
 * Compute total field magnitude in Gauss.
 */
float field_engine_magnitude(const field_vector_t *field);

/**
 * Classify dominant pole based on Z-axis field direction
 * relative to the horizontal field magnitude.
 */
pole_t field_engine_dominant_pole(const field_vector_t *field);

#endif /* FIELD_ENGINE_H_ */