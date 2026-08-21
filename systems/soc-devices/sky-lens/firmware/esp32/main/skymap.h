/* skymap.h — 64×32 (az×zen) celestial muon-flux histogram */
#ifndef SKYMAP_H
#define SKYMAP_H
#include "sky_lens.h"

void      skymap_init(void);
void      skymap_add_event(float zenith_deg, float az_deg);
void      skymap_clear(void);
void      skymap_get(skymap_t *out);
uint32_t  skymap_total(void);

#endif