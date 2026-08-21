/*
 * pyro-balance / Core/Inc/purge.h
 */
#ifndef PURGE_H
#define PURGE_H
#include "main.h"
void purge_init(void);
void purge_set_n2(bool on);
void purge_pump_on(bool on);
void purge_set_flow_ml_per_min(float ml_min);
float purge_read_flow(void);
#endif