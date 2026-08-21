/*
 * adc.h — 500 ksps photodiode sampling via DMA + circular buffer
 *
 * Hardware:
 *   PA0 (ADC1_IN1) ◀─ photodiode TIA output (0–3.3 V)
 *
 * ADC1 runs at 500 ksps, 12-bit, circular DMA into a 1024-sample
 * buffer. The half-transfer and full-transfer interrupts feed
 * the pulse detector. A pulse-detect callback is invoked for each
 * detected particle event, passing the bin index and peak voltage.
 */

#ifndef ADC_H
#define ADC_H

#include <stdint.h>
#include <stdbool.h>

#define ADC_SAMPLE_RATE_HZ   500000u
#define ADC_DMA_BUF_LEN      1024u

typedef void (*pulse_cb_t)(uint8_t bin, float peak_v);

void   adc_init(void);
void   adc_start_sampling(pulse_cb_t cb);
void   adc_stop_sampling(void);
const uint16_t *adc_buffer(void);
uint32_t adc_buffer_count(void);

#endif /* ADC_H */