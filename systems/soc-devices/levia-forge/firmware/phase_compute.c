/*
 * Levia Forge — Phase Computation
 * Computes per-element phase delays for acoustic focusing.
 *
 * For a desired focal point p = (px, py, pz), the phase for each
 * transducer i at position t_i is:
 *
 *   φ_i = (2π · f / c) · |t_i - p|
 *
 * where f = 40 kHz, c = 343 m/s. The phase is quantized to 256 steps.
 *
 * SPDX-License-Identifier: MIT
 */
#include "phase_compute.h"
#include "transducer_layout.h"
#include "sdkconfig.h"
#include <math.h>

#define TWO_PI       6.28318530717958647692f
#define WAVELENGTH   (SPEED_OF_SOUND / CARRIER_FREQ_HZ)  /* ~8.575 mm */

/* Phase buffer: 256 steps × 72 bits packed into 9 bytes per step.
 * Each step is 9 bytes (72 bits). Total = 256 × 9 = 2304 bytes.
 * Bit i in step s is 1 if (s < phase_step_i) XOR (phase_step_i < 128)?
 * No — the square wave is HIGH for the first half and LOW for the
 * second half, offset by phase_step_i.
 *
 * For a 50% duty square wave with phase_step_i:
 *   bit[i] at step s = 1 if ((s - phase_step_i) mod 256) < 128
 * This gives a square wave that transitions HIGH→LOW at step
 * (phase_step_i + 128) mod 256, and LOW→HIGH at phase_step_i.
 */

static uint8_t phase_buffer[DMA_BUFFER_SIZE];
static uint8_t phase_steps[NUM_TRANSDUCERS];  /* current phase step (0-255) for each transducer */

void phase_compute_init(void)
{
    for (int i = 0; i < DMA_BUFFER_SIZE; i++)
        phase_buffer[i] = 0;
    for (int i = 0; i < NUM_TRANSDUCERS; i++)
        phase_steps[i] = 0;
}

/*
 * Compute phase steps for a single focal point.
 * px, py, pz in mm.
 */
void phase_compute_point(float px, float py, float pz)
{
    const transducer_pos_t *positions = transducer_get_positions();
    const float k = TWO_PI / WAVELENGTH;  /* wavenumber in rad/mm */

    for (int i = 0; i < NUM_TRANSDUCERS; i++) {
        float dx = positions[i].x - px;
        float dy = positions[i].y - py;
        float dz = positions[i].z - pz;
        float dist = sqrtf(dx * dx + dy * dy + dz * dz);
        float phase_rad = k * dist;
        /* Normalize to [0, 2π) and quantize to 256 steps */
        float normalized = fmodf(phase_rad, TWO_PI);
        if (normalized < 0) normalized += TWO_PI;
        phase_steps[i] = (uint8_t)((normalized / TWO_PI) * PHASE_STEPS);
    }
    phase_pack_buffer();
}

/*
 * Compute phase for twin trap: two focal points separated by delta_x.
 */
void phase_compute_twin(float px, float py, float pz, float delta)
{
    const transducer_pos_t *positions = transducer_get_positions();
    const float k = TWO_PI / WAVELENGTH;

    /* Half the transducers focus on point A, half on point B.
     * Simpler approach: use the phase that creates two pressure maxima.
     * We split top array → point A, bottom array → point B.
     * Actually, for a twin trap, the standard method is to superimpose
     * two holograms. Here we use: alternate phases between two foci. */
    float ax = px - delta / 2.0f;
    float bx = px + delta / 2.0f;

    for (int i = 0; i < NUM_TRANSDUCERS; i++) {
        float tx = (i % 2 == 0) ? ax : bx;
        float dx = positions[i].x - tx;
        float dy = positions[i].y - py;
        float dz = positions[i].z - pz;
        float dist = sqrtf(dx * dx + dy * dy + dz * dz);
        float phase_rad = k * dist;
        float normalized = fmodf(phase_rad, TWO_PI);
        if (normalized < 0) normalized += TWO_PI;
        phase_steps[i] = (uint8_t)((normalized / TWO_PI) * PHASE_STEPS);
    }
    phase_pack_buffer();
}

/*
 * Compute vortex trap: add azimuthal phase gradient (topological charge ℓ).
 */
void phase_compute_vortex(float px, float py, float pz, int topological_charge)
{
    const transducer_pos_t *positions = transducer_get_positions();
    const float k = TWO_PI / WAVELENGTH;

    for (int i = 0; i < NUM_TRANSDUCERS; i++) {
        /* Distance to focal point */
        float dx = positions[i].x - px;
        float dy = positions[i].y - py;
        float dz = positions[i].z - pz;
        float dist = sqrtf(dx * dx + dy * dy + dz * dz);
        float phase_rad = k * dist;

        /* Add azimuthal component: ℓ × θ where θ = atan2(dy, dx) */
        float theta = atan2f(dy, dx);
        phase_rad += (float)topological_charge * theta;

        float normalized = fmodf(phase_rad, TWO_PI);
        if (normalized < 0) normalized += TWO_PI;
        phase_steps[i] = (uint8_t)((normalized / TWO_PI) * PHASE_STEPS);
    }
    phase_pack_buffer();
}

/*
 * Compute bending trap: linear phase gradient along X axis.
 * This creates a tilted pressure field that pushes the particle.
 */
void phase_compute_bending(float px, float py, float pz, float gradient)
{
    const transducer_pos_t *positions = transducer_get_positions();
    const float k = TWO_PI / WAVELENGTH;

    for (int i = 0; i < NUM_TRANSDUCERS; i++) {
        float dx = positions[i].x - px;
        float dy = positions[i].y - py;
        float dz = positions[i].z - pz;
        float dist = sqrtf(dx * dx + dy * dy + dz * dz);
        float phase_rad = k * dist;
        /* Add linear gradient proportional to transducer X position */
        phase_rad += gradient * positions[i].x;

        float normalized = fmodf(phase_rad, TWO_PI);
        if (normalized < 0) normalized += TWO_PI;
        phase_steps[i] = (uint8_t)((normalized / TWO_PI) * PHASE_STEPS);
    }
    phase_pack_buffer();
}

/*
 * Compute transport (conveyor) trap: a line trap that moves over time.
 * The `progress` parameter (0.0–1.0) sweeps the trap along X.
 */
void phase_compute_transport(float py, float pz, float progress,
                             float sweep_range)
{
    float px = -sweep_range + 2.0f * sweep_range * progress;
    phase_compute_point(px, py, pz);
}

/*
 * Pack phase_steps[] into the DMA phase_buffer.
 *
 * Buffer layout: 256 steps × 9 bytes = 2304 bytes.
 * At step s, byte b = bits [8b .. 8b+7] of the 72-bit output.
 * Bit i at step s = ((s - phase_steps[i]) & 0xFF) < 128 ? 1 : 0
 *
 * This produces a 50% duty square wave at 40 kHz with the correct
 * phase offset for each transducer.
 */
void phase_pack_buffer(void)
{
    for (int s = 0; s < PHASE_STEPS; s++) {
        int byte_offset = s * 9;  /* 9 bytes per step (72 bits) */
        for (int b = 0; b < 9; b++) {
            uint8_t val = 0;
            for (int bit = 0; bit < 8; bit++) {
                int elem = b * 8 + bit;
                if (elem >= NUM_TRANSDUCERS)
                    break;
                int shifted = (s - phase_steps[elem]) & 0xFF;
                if (shifted < 128)
                    val |= (1 << bit);
            }
            phase_buffer[byte_offset + b] = val;
        }
    }
}

uint8_t *phase_get_buffer(void)
{
    return phase_buffer;
}

const uint8_t *phase_get_steps(void)
{
    return phase_steps;
}