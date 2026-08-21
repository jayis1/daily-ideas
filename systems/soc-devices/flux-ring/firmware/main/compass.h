/*
 * Flux Ring — compass.h
 * Tilt-compensated digital compass.
 */

#ifndef COMPASS_H_
#define COMPASS_H_

#include "field_engine.h"
#include "accel_sensor.h"
#include <stdint.h>

typedef uint16_t compass_heading_t;  /* 0-359 degrees */

/**
 * Compute tilt-compensated compass heading.
 * @param field   Tilt-compensated magnetic field vector
 * @param accel   Accelerometer data (for tilt reference)
 * @return        Heading in degrees (0=North, 90=East, 180=South, 270=West)
 */
compass_heading_t compass_compute(const field_vector_t *field,
                                  const accel_data_t *accel);

/**
 * Get cardinal direction string from heading.
 */
const char *compass_cardinal(compass_heading_t heading);

#endif /* COMPASS_H_ */