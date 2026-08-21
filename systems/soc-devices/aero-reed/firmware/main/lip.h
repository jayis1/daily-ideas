/*
 * lip.h — lip/bite force sensor (FSR-402)
 */
#pragma once
#include <stdint.h>

void   lip_init(void);
void   lip_scan(void);
int16_t lip_get_bend_cents(void);  /* -8192..+8192 (14-bit MIDI pitch bend units) */
uint8_t lip_get_brightness(void);  /* 0..127 → CC74 */
float  lip_get_force(void);        /* 0..1 raw force */