/*
 * adc.h — STM32G474 ADC1: 3.6 Msps ToF capture + 28 ksps BUA oversample
 */

#ifndef ADC_H
#define ADC_H

#include <stdint.h>

void          adc_init(void);
void          adc_start_tof_capture(void);   /* 3.6 Msps, 115k samples, DMA */
void          adc_wait_tof_done(void);
void          adc_start_bua_capture(void);    /* 28 ksps oversampled, 1400 samples */
void          adc_wait_bua_done(void);
const uint16_t* adc_tof_buffer(void);
const uint16_t* adc_bua_buffer(void);
void          adc_stop(void);

#endif