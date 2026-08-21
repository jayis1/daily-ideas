/*
 * Flux Ring — field_engine.c
 * Tilt-compensated magnetic field processing engine.
 *
 * SPDX-License-Identifier: MIT
 */

#include "field_engine.h"
#include <zephyr/logging/log.h>
#include <math.h>

LOG_MODULE_DECLARE(field_engine, LOG_LEVEL_INF);

field_vector_t field_engine_compensate(const mag_data_t *mag,
                                       const accel_data_t *accel)
{
    field_vector_t result;

    /* Store raw values */
    result.x_raw = mag->x;
    result.y_raw = mag->y;
    result.z_raw = mag->z;

    /* Compute roll and pitch from accelerometer */
    float ax = accel->x;
    float ay = accel->y;
    float az = accel->z;

    /* Normalize acceleration vector */
    float a_mag = sqrtf(ax * ax + ay * ay + az * az);
    if (a_mag < 0.01f) {
        /* Invalid accelerometer reading — return raw data */
        result.x = mag->x;
        result.y = mag->y;
        result.z = mag->z;
        return result;
    }

    /* Roll (phi): rotation around X axis */
    float roll = atan2f(ay, az);

    /* Pitch (theta): rotation around Y axis */
    float pitch;
    if (fabsf(ay * sinf(roll) + az * cosf(roll)) < 1e-6f) {
        pitch = atan2f(-ax, 1.0f);
    } else {
        pitch = atan2f(-ax, ay * sinf(roll) + az * cosf(roll));
    }

    /* Tilt compensation:
     * Rotate magnetic vector from sensor frame to horizontal frame
     *
     * Mx_h = Mx*cos(pitch) + My*sin(roll)*sin(pitch) + Mz*cos(roll)*sin(pitch)
     * My_h = My*cos(roll) - Mz*sin(roll)
     */
    float cos_pitch = cosf(pitch);
    float sin_pitch = sinf(pitch);
    float cos_roll  = cosf(roll);
    float sin_roll  = sinf(roll);

    float mx = mag->x;
    float my = mag->y;
    float mz = mag->z;

    result.x = mx * cos_pitch + my * sin_roll * sin_pitch + mz * cos_roll * sin_pitch;
    result.y = my * cos_roll - mz * sin_roll;
    result.z = mz;  /* Z unchanged (vertical component) */

    return result;
}

float field_engine_magnitude(const field_vector_t *field)
{
    return sqrtf(field->x * field->x +
                 field->y * field->y +
                 field->z * field->z);
}

pole_t field_engine_dominant_pole(const field_vector_t *field)
{
    /* Classify based on Z-axis field relative to horizontal magnitude:
     * Strong positive Z → North pole below sensor
     * Strong negative Z → South pole below sensor
     * Weak Z → ambient / symmetric
     */
    float h_mag = sqrtf(field->x * field->x + field->y * field->y);
    float z = field->z;

    /* Only classify if Z component is significant relative to horizontal */
    if (fabsf(z) > h_mag * 0.3f && fabsf(z) > 0.3f) {
        /* Z > 0: field lines going upward from below = approaching N pole */
        if (z > 0) return POLE_N;
        else       return POLE_S;
    }

    /* Also check if horizontal field is very strong (near a pole) */
    if (h_mag > 5.0f) {
        /* Strong horizontal — could be near a magnet's equator */
        if (z > 0.5f) return POLE_N;
        if (z < -0.5f) return POLE_S;
    }

    return POLE_NONE;
}