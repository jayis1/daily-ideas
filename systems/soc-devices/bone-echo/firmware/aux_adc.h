/*
 * aux_adc.h — ADS1115 aux channel reads (temp, etc.)
 */

#ifndef AUX_ADC_H
#define AUX_ADC_H

void  aux_adc_init(void);
float aux_adc_read(int channel);   /* 0–3, returns volts */
float aux_adc_read_temp(void);      /* DS18B20 temperature via 1-Wire */

#endif