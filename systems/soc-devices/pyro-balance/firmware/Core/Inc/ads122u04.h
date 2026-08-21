/*
 * pyro-balance / Core/Inc/ads122u04.h
 * ADS122U04 24-bit ADC driver (I²C) — PT1000 4-wire RTD.
 */
#ifndef ADS122U04_H
#define ADS122U04_H

#include "main.h"

#define ADS122U04_ADDR        (0x48 << 1)  /* I²C 7-bit 0x48 */
#define ADS122U04_REG_CONFIG0 0x00
#define ADS122U04_REG_CONFIG1 0x01
#define ADS122U04_REG_CONFIG2 0x02
#define ADS122U04_REG_CONFIG3 0x03

void  ads_init(void);
void  ads_set_rtd_mode(void);     /* 4-wire RTD, 250 µA excitation, PGA=1 */
float ads_read_temp_c(void);      /* blocking; RTD temp from ratiometric read */
float ads_read_volts(void);       /* raw voltage */
void  ads_start_conversion(void);
bool  ads_ready(void);
int32_t ads_read_raw(void);       /* 24-bit signed */

/* Callendar–Van Dusen: R(t) = R0*(1 + A*t + B*t^2) for t>=0 */
float rtd_resistance_to_temp(float r_ohm);

#endif /* ADS122U04_H */