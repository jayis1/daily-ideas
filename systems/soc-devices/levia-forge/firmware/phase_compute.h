/*
 * Levia Forge — Phase Computation Header
 * SPDX-License-Identifier: MIT
 */
#ifndef PHASE_COMPUTE_H
#define PHASE_COMPUTE_H

#include <stdint.h>
#include "sdkconfig.h"

void phase_compute_init(void);

/* Single focal point trap */
void phase_compute_point(float px, float py, float pz);

/* Twin trap: two foci separated by delta (mm) in X */
void phase_compute_twin(float px, float py, float pz, float delta);

/* Vortex trap: topological charge ℓ (1 = single vortex, 2 = double) */
void phase_compute_vortex(float px, float py, float pz, int topological_charge);

/* Bending trap: linear phase gradient along X */
void phase_compute_bending(float px, float py, float pz, float gradient);

/* Transport (conveyor): moving line trap, progress 0.0–1.0 */
void phase_compute_transport(float py, float pz, float progress, float sweep_range);

/* Pack current phase_steps into DMA buffer */
void phase_pack_buffer(void);

/* Get DMA buffer pointer (2304 bytes) */
uint8_t *phase_get_buffer(void);

/* Get current phase steps array (72 entries) */
const uint8_t *phase_get_steps(void);

#endif /* PHASE_COMPUTE_H */