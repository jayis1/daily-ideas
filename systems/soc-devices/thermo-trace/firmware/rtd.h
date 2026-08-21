/*
 * rtd.h — PT1000 RTD temperature conversion (header)
 */
#ifndef RTD_H
#define RTD_H

#include <stdint.h>

#define RTD_R0          1000.0f   /* PT1000: 1000Ω at 0°C */
#define RTD_ALPHA       0.00385f  /* platinum coefficient */
#define RTD_A           3.9083e-3f
#define RTD_B           -5.775e-7f
#define RTD_C_NEG       -4.183e-12f  /* for T<0, Callendar-Van Dusen */
#define RTD_R_REF       4000.0f   /* reference resistor for IDAC circuit */

float rtd_r_to_temp(float resistance);
float rtd_temp_to_r(float temp);
float rtd_v_to_r(float voltage, float idac_current);
float rtd_linearize(float resistance);

#endif /* RTD_H */