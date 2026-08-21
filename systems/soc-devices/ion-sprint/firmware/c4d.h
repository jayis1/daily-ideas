/*
 * c4d.h — Contactless conductivity detection (C4D)
 */

#ifndef C4D_H
#define C4D_H

#include <stdbool.h>
#include <stdint.h>

/* Initialize C4D: DAC2 (100 kHz AC excitation), ADC1 (200 kHz capture),
 * CORDIC lock-in I/Q demodulation. */
void c4d_init(void);

/* Start acquiring electropherogram into buffer (100 Hz effective rate).
 * Simultaneously drives DAC2 AC excitation to the C4D driver electrode. */
void c4d_start_acquisition(float *buffer, uint32_t max_samples);

/* Stop acquisition */
void c4d_stop_acquisition(void);

/* Check if still acquiring */
bool c4d_is_acquiring(void);

/* Get number of samples acquired so far */
uint32_t c4d_get_sample_count(void);

/* Lock-in demodulation: process raw ADC block → electropherogram points.
 * Called from DMA interrupt or main loop. */
void c4d_process_block(const uint16_t *raw, uint32_t count);

#endif /* C4D_H */