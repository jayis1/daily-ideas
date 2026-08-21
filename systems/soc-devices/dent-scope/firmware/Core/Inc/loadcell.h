/*
 * dent-scope / Core/Inc/loadcell.h
 * Dent Scope — HX711 24-bit load cell driver (force measurement)
 * MIT License.
 */
#ifndef LOADCELL_H
#define LOADCELL_H

#include "main.h"

void  loadcell_init(void);
void  loadcell_read_mN(void);
float loadcell_last_mN(void);
void  loadcell_tare(void);

#endif /* LOADCELL_H */