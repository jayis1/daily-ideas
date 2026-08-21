/*
 * detect.h — CFAR sferic detector + feature extraction
 */
#ifndef BOLT_COMPASS_DETECT_H
#define BOLT_COMPASS_DETECT_H

#include "types.h"

/* Initialize detector state (noise floor = quiet baseline). */
void detect_init(void);

/* Run the CFAR detector over the ring. If a sferic is found, fill `out`
 * with features + the 50 ms waveform window and return 1. Called from
 * the sferic core task at ~100 Hz (every 10 ms of new data). */
int  detect_sferic(ring_t *r, sferic_t *out);

/* Current noise floor estimate (for OLED / app display). */
float detect_noise_floor(void);

#endif /* BOLT_COMPASS_DETECT_H */