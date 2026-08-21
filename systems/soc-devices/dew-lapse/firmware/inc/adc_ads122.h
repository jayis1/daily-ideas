/* adc_ads122.h — ADS122U04 24-bit ADC for mirror thermistors */
#ifndef ADC_ADS122_H
#define ADC_ADS122_H

int ads122_init(void);
int ads122_read_mirror(float *t_mirror, float *t_ref, float *dt);
int ads122_fault(float t_mirror);

#endif