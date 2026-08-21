/*
 * stiffness.h — Stiffness Index: SI = 0.67·BUA + 0.28·SOS − 420
 */

#ifndef STIFFNESS_H
#define STIFFNESS_H

void  stiffness_init(void);
float stiffness_compute(float bua_db_mhz, float sos_mps);

#endif