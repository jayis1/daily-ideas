/* adc.h — ADS7946 dual 14-bit SAR ADC driver (pulse-height capture) */
#ifndef ADC_H
#define ADC_H
#include "sky_lens.h"

void adc_init(void);
void adc_trigger_and_read(int16_t *h0_mv, int16_t *h1_mv);
void adc_deinit(void);

#endif