/*
 * bearing.h — crossed-loop goniometer + 180° ambiguity resolution
 */
#ifndef BOLT_COMPASS_BEARING_H
#define BOLT_COMPASS_BEARING_H

#include "types.h"

/* Compute the azimuth (0..360°, 0=N, clockwise) to the stroke from the
 * two loop peaks + the E-field sign. */
float bearing_compute(const sferic_t *s);

#endif /* BOLT_COMPASS_BEARING_H */