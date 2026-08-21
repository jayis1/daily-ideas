/*
 * adc.h — ADC1 oversampled sampling at 28 ksps with DMA double-buffer
 */
#ifndef ADC_H
#define ADC_H

#include <stdint.h>
#include <stdbool.h>

#define ADC_BLOCK_SIZE 256   /* 256 oversampled raw samples → 1 16-bit result */

void adc_init(void);
void adc_start(void);
void adc_stop(void);

/* Returns the latest 16-bit oversampled sample (0..65535), blocks until ready.
 * Called by the demodulator at f_s = 28 ksps. */
int32_t adc_get_sample(void);

/* Non-blocking: returns true if a fresh sample is available. */
bool adc_sample_ready(void);

/* Pre-PGA signal monitor (ADC2 channel 3), for input protection. */
float adc_read_signal_monitor(void);

/* Battery voltage (PA4 divider 2:1) */
float adc_read_battery(void);

#endif /* ADC_H */