/*
 * Phase Scope — ADC driver header
 */

#ifndef ADC_H
#define ADC_H

#include <stdint.h>

#define SAMPLES_PER_CHANNEL 1024
#define NUM_CHANNELS         6

extern volatile uint16_t adc_buffer_a[];
extern volatile uint16_t adc_buffer_b[];
extern volatile uint8_t  adc_buffer_ready;
extern volatile uint16_t ntc_raw;
extern volatile uint16_t vbat_raw;

void adc_init(void);
uint16_t *adc_get_buffer(uint8_t *which);
void adc_read_slow_channels(void);

#endif /* ADC_H */