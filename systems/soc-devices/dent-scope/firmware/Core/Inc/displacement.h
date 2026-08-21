/*
 * dent-scope / Core/Inc/displacement.h
 * Dent Scope — AD7746 capacitive depth sensor driver
 * MIT License.
 */
#ifndef DISPLACEMENT_H
#define DISPLACEMENT_H

#include "main.h"

void  displacement_init(void);
void  displacement_read_um(void);
float displacement_last_um(void);
float displacement_raw_pf(void);

#endif /* DISPLACEMENT_H */