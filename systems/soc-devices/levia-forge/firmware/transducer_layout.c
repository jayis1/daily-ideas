/*
 * Levia Forge — Transducer 3D Layout
 * Defines the 3D positions of all 72 ultrasonic transducers.
 *
 * SPDX-License-Identifier: MIT
 */
#include "transducer_layout.h"
#include <math.h>
#include "sdkconfig.h"

/*
 * Each array is a 6×6 grid of transducers on a curved (spherical) mount.
 * The curvature focuses energy toward the center.
 *
 * Coordinate system (mm):
 *   X: left-right (columns 0-5, centered at 0)
 *   Y: front-back (rows 0-5, centered at 0)
 *   Z: up-down (top array at +35, bottom at -35)
 *
 * For a spherical cap of radius R centered at the origin (0,0,0),
 * a point at grid position (col, row) is at:
 *   x = (col - 2.5) * spacing
 *   y = (row - 2.5) * spacing
 *   z = top:  +sqrt(R² - x² - y²) - (R - top_z)   → approximately top_z
 *      bottom: -(sqrt(R² - x² - y²) - (R - |bottom_z|))
 *
 * Simplified: for each element, compute the spherical cap offset.
 */

static transducer_pos_t transducer_positions[NUM_TRANSDUCERS];

static void compute_array_positions(int start_idx, float z_plane, int direction)
{
    /* direction: +1 = top (pointing down, normal toward -Z),
     *           -1 = bottom (pointing up, normal toward +Z) */
    const float spacing = ELEMENT_SPACING_MM;  /* 10 mm */
    const float R = CURVATURE_RADIUS_MM;        /* 40 mm */
    const float half = (ARRAY_COLS - 1) / 2.0f; /* 2.5 */

    for (int row = 0; row < ARRAY_ROWS; row++) {
        for (int col = 0; col < ARRAY_COLS; col++) {
            int idx = start_idx + row * ARRAY_COLS + col;
            float x = (col - half) * spacing;
            float y = (row - half) * spacing;
            /* radial distance from center axis */
            float r_sq = x * x + y * y;
            /* z offset from the spherical cap: z = R - sqrt(R² - r²) */
            float z_offset = 0.0f;
            if (r_sq < R * R) {
                z_offset = R - sqrtf(R * R - r_sq);
            }
            /* The transducer sits on the curved mount.
             * For the top array: the center is at z_plane (35 mm),
             *   and outer elements curve upward (away from center).
             *   So z = z_plane + z_offset (higher up).
             * For the bottom array: center at z_plane (-35 mm),
             *   outer elements curve downward.
             *   So z = z_plane - z_offset. */
            if (direction > 0) {
                transducer_positions[idx].x = x;
                transducer_positions[idx].y = y;
                transducer_positions[idx].z = z_plane + z_offset;
            } else {
                transducer_positions[idx].x = x;
                transducer_positions[idx].y = y;
                transducer_positions[idx].z = z_plane - z_offset;
            }
            /* Normal direction (pointing toward the trap center at origin) */
            /* Normal = normalize(origin - position) */
            float nx = -transducer_positions[idx].x;
            float ny = -transducer_positions[idx].y;
            float nz = -transducer_positions[idx].z;
            float nlen = sqrtf(nx * nx + ny * ny + nz * nz);
            if (nlen > 0.001f) {
                transducer_positions[idx].nx = nx / nlen;
                transducer_positions[idx].ny = ny / nlen;
                transducer_positions[idx].nz = nz / nlen;
            }
        }
    }
}

void transducer_layout_init(void)
{
    /* Top array: indices 0-35, at z = +35 mm, pointing down */
    compute_array_positions(0, TOP_ARRAY_Z_MM, +1);
    /* Bottom array: indices 36-71, at z = -35 mm, pointing up */
    compute_array_positions(NUM_TOP, BOTTOM_ARRAY_Z_MM, -1);
}

const transducer_pos_t *transducer_get_positions(void)
{
    return transducer_positions;
}

const transducer_pos_t *transducer_get(int idx)
{
    if (idx < 0 || idx >= NUM_TRANSDUCERS)
        return NULL;
    return &transducer_positions[idx];
}