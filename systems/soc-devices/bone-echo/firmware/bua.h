/*
 * bua.h — BUA: FFT, attenuation vs frequency, linear fit 0.2–0.6 MHz
 */

#ifndef BUA_H
#define BUA_H

#include <stdint.h>
#include <stdbool.h>

void  bua_init(void);
float bua_compute(const uint16_t *bua_buf, uint32_t n,
                  const float *ref_fft);
float bua_last_r2(void);
float bua_last_intercept(void);

#endif