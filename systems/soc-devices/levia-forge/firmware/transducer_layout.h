/*
 * Levia Forge — Transducer 3D Layout Header
 * SPDX-License-Identifier: MIT
 */
#ifndef TRANSDUCER_LAYOUT_H
#define TRANSDUCER_LAYOUT_H

#include <stdint.h>

typedef struct {
    float x, y, z;      /* position in mm */
    float nx, ny, nz;   /* unit normal (pointing toward trap center) */
} transducer_pos_t;

void transducer_layout_init(void);
const transducer_pos_t *transducer_get_positions(void);
const transducer_pos_t *transducer_get(int idx);

#endif /* TRANSDUCER_LAYOUT_H */