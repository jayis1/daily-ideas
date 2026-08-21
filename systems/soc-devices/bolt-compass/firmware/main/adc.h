/*
 * adc.h — ADS131M04 4-channel 24-bit simultaneous-sampling ADC driver
 */
#ifndef BOLT_COMPASS_ADC_H
#define BOLT_COMPASS_ADC_H

#include "types.h"

/* Initialize the ADS131M04: 8 ksps, PGA x8, continuous conversion,
 * DRDY falling-edge interrupt → adc_isr() → ring buffer in PSRAM.
 * Returns 0 on success. */
int  adc_init(void);

/* ISR body — call from the GPIO DRDY edge handler. Copies one 4-ch sample
 * from the ADS131M04 SPI into the ring buffer and advances wr. */
void adc_isr(void);

/* Snapshot the latest RING_LEN samples into a linear buffer (caller-owned).
 * Returns the GPS timestamp of the newest sample. */
uint64_t adc_snapshot(sample_t *out, int n);

/* Direct access to the ring (for the detector). */
ring_t *adc_ring(void);

/* Power-down the ADC for deep sleep. */
void adc_sleep(void);
void adc_wake(void);

#endif /* BOLT_COMPASS_ADC_H */