/*
 * freqcount.h — 32-bit timer frequency counter
 */

#ifndef QUARTZ_TUNER_FREQCOUNT_H
#define QUARTZ_TUNER_FREQCOUNT_H

#include <stdint.h>

int freqcount_init(void);
uint32_t freqcount_measure(float gate_time_s);

#endif