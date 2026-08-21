/*
 * pga.h — PGA204 + PGA113 programmable-gain front-end control
 */
#ifndef PGA_H
#define PGA_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    PGA_GAIN_1   = 0,   /* 1×    */
    PGA_GAIN_2   = 1,   /* 2×    */
    PGA_GAIN_4   = 2,   /* 4×    */
    PGA_GAIN_8   = 3,   /* 8×    */
    PGA_GAIN_16  = 4,
    PGA_GAIN_32  = 5,
    PGA_GAIN_64  = 6,
    PGA_GAIN_128 = 7,
    PGA_GAIN_256 = 8,
    PGA_GAIN_512 = 9,
    PGA_GAIN_1024 = 10,
} pga_gain_t;

void pga_init(void);
void pga_set_gain(pga_gain_t g);
pga_gain_t pga_get(void);
float pga_get_gain(void);   /* numeric (1..1024) */

/* Auto-range: sets gain so the signal monitor is in 30%..80% of full-scale.
 * Returns true if gain changed. */
bool pga_auto_range(void);

#endif /* PGA_H */