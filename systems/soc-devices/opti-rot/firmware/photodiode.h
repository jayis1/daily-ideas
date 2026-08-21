/*
 * photodiode.h — TSL257 light-to-voltage sensor ADC driver
 * Reads photodiode output via ADC1 Channel 2 (PA2) with oversampling.
 */
#ifndef PHOTODIODE_H
#define PHOTODIODE_H

#include <stdint.h>

#define PHOTODIODE_ADC_MAX   4095   /* 12-bit ADC */

void photodiode_init(void);

/* Read raw ADC value (single conversion) */
uint16_t photodiode_read_raw(void);

/* Read oversampled (averaged) value — n samples */
uint16_t photodiode_oversample(uint16_t n);

/* Read normalized intensity (0.0 to 1.0) */
double photodiode_read_normalized(void);

/* Check if signal is above minimum threshold */
uint8_t photodiode_signal_ok(void);

#endif /* PHOTODIODE_H */