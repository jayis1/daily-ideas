/*
 * trajectory_recon.h — 3D trajectory reconstruction API
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#ifndef TRAJECTORY_RECON_H
#define TRAJECTORY_RECON_H

#include "imu_driver.h"
#include "stroke_segmenter.h"

#define MAX_TRAJ_POINTS  128

/* 2D trajectory point (after projection onto writing plane) */
typedef struct {
    float x;  /* 0.0 to 1.0 (normalized) */
    float y;  /* 0.0 to 1.0 (normalized, Y-inverted) */
} traj_point_t;

/* Complete 2D trajectory for a single character */
typedef struct {
    traj_point_t points[MAX_TRAJ_POINTS];
    int point_count;
} traj_2d_t;

/**
 * @brief Initialize the trajectory reconstructor.
 */
void trajectory_recon_init(void);

/**
 * @brief Set sample time step (1/ODR).
 */
void trajectory_recon_set_dt(float sample_dt);

/**
 * @brief Set magnetometer heading for yaw correction.
 * @param heading_rad  Heading in radians
 */
void trajectory_recon_set_mag_heading(float heading_rad);

/**
 * @brief Reconstruct 2D trajectory from a stroke event.
 *
 * Uses Madgwick orientation filter + double integration to
 * reconstruct the pen path, then projects onto the writing
 * plane (XY in world frame). Normalizes to 0.0-1.0 range.
 *
 * @param stroke  Input stroke event from segmenter
 * @param traj    Output 2D trajectory
 */
void trajectory_recon_project(const stroke_event_t *stroke, traj_2d_t *traj);

#endif /* TRAJECTORY_RECON_H */