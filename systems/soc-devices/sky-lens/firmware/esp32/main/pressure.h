/* pressure.h — BMP390 barometric pressure + temperature + correction */
#ifndef PRESSURE_H
#define PRESSURE_H
#include "sky_lens.h"

void  pressure_init(void);
float pressure_read_hpa(void);        /* current pressure, hPa */
float pressure_read_temp_c(void);      /* current temperature, °C */
float pressure_correct_rate(float rate_cpm, float p_hpa, float t_c); /* barometric correction */

#endif