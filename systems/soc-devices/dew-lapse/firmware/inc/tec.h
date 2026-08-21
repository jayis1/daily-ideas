/* tec.h — TEC driver interface */
#ifndef TEC_H
#define TEC_H

void  tec_init(void);
void  tec_set(float frac);          /* [-1.0, +1.0] */
void  tec_off(void);
void  tec_defrost_start(void);
void  tec_defrost_stop(void);
void  tec_sense_update(void);
float tec_current(void);
float tec_voltage(void);
int   tec_safety_ok(float hot_temp_c);

#endif