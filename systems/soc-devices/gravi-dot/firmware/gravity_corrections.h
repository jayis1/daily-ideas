/**
 * gravity_corrections.h — gravimetric correction functions
 */
#ifndef GRAVITY_CORRECTIONS_H
#define GRAVITY_CORRECTIONS_H

#include <stdint.h>

/**
 * Longman earth-tide correction (simplified).
 * Computes the lunar + solar gravitational tide effect at a given
 * time and location. Returns correction in milliGal.
 *
 * @param unix_time  UTC seconds since epoch
 * @param lat_deg    station latitude (degrees)
 * @param lon_deg    station longitude (degrees)
 * @return tide correction in mGal (add to measured g)
 */
double longman_tide(uint32_t unix_time, double lat_deg, double lon_deg);

#endif /* GRAVITY_CORRECTIONS_H */