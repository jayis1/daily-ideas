/*
 * electrometer.h — ADA4530-1 TIA + ADS122U04 + STM32 ADC1 40 ksps capture
 * Iono Pin — Pocket Ion Mobility Spectrometer (IMS)
 */
#ifndef ELECTROMETER_H
#define ELECTROMETER_H

#include <stdint.h>
#include <stdbool.h>

#define EM_SAMPLES 140   /* 0.5-3.5 ms @ 40 ksps */

void electrometer_init(void);

/* Start a DMA capture of one sweep (140 samples). Blocks until done. */
void electromer_capture(int16_t *out, uint16_t n);

/* Non-blocking: returns true when a sweep is ready in the DMA buffer */
bool electrometer_sweep_ready(void);
void electrometer_get(int16_t *out, uint16_t n);

#endif /* ELECTROMETER_H */