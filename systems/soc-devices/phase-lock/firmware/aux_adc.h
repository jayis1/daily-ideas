/*
 * aux_adc.h — ADS1115 16-bit aux ADC for slow aux inputs (thermistor, etc.)
 */
#ifndef AUX_ADC_H
#define AUX_ADC_H

#include <stdint.h>

void aux_adc_init(void);

/* Read a single-ended channel (0..3) in Volts. */
float aux_adc_read(uint8_t channel);

/* Read the differential AIN0-AIN1 (V). */
float aux_adc_read_diff01(void);

#endif /* AUX_ADC_H */