/*
 * heel_caliper.h — Caliper pot → heel width d (mm)
 */

#ifndef HEEL_CALIPER_H
#define HEEL_CALIPER_H

void  heel_caliper_init(void);
float heel_caliper_read_mm(void);
void  heel_caliper_calibrate_zero(void);
void  heel_caliper_calibrate_full(void);

#endif