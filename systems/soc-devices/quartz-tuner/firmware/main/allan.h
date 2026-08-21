/*
 * allan.h — Allan deviation computation
 *
 * Measures frequency stability at τ = 0.1 s, 1 s, and 10 s
 * using the STM32G491's 32-bit timer input capture.
 */

#ifndef QUARTZ_TUNER_ALLAN_H
#define QUARTZ_TUNER_ALLER_H

#include "types.h"

/* Measure Allan deviation using timer input capture.
 * The crystal oscillates at f_s (set by Si5351A), and the
 * STM32G491 counts periods against the HSI16 reference.
 * At least 100 samples per tau are needed for a meaningful result. */
int allan_measure(allan_dev_t *allan, const sweep_t *sweep,
                  const calibration_t *cal);

#endif /* QUARTZ_TUNER_ALLAN_H */