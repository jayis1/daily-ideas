/*
 * library.h — 40-ion migration-time library + k-NN identification
 */

#ifndef LIBRARY_H
#define LIBRARY_H

#include <stdint.h>

/* Initialize ion library (loads from flash) */
void library_init(void);

/* Identify an ion from normalized migration time + peak skewness.
 * Returns ion index (0–39) or -1 if no match within tolerance. */
int8_t library_identify(float norm_mt, float skewness, uint8_t bge_recipe);

/* Get ion name by index */
const char *library_get_name(uint8_t index);

/* Get expected migration time for an ion (under reference BGE) */
float library_get_mt(uint8_t index, uint8_t bge_recipe);

/* Number of ions in library */
uint8_t library_size(void);

#endif /* LIBRARY_H */