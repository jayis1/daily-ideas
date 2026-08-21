/*
 * skymap.c — 64×32 (az × zen) celestial muon-flux histogram
 *
 * Each coincidence event is mapped onto a 64×32 cell grid (azimuth
 * 0..360°, zenith 0..90°) using the reconstructed track angle + the
 * device attitude. Long integrations build up a "muon sky map" that
 * shows the cos²θ angular distribution and, with enough events, the
 * ~1% muon deficit at the Sun/Moon position (the muon shadow).
 */
#include "skymap.h"
#include "sky_lens.h"
#include <string.h>

static skymap_t s_map;

void skymap_init(void)
{
    skymap_clear();
}

void skymap_clear(void)
{
    memset(&s_map, 0, sizeof(s_map));
}

void skymap_add_event(float zenith_deg, float az_deg)
{
    /* Clip zenith to [0, 90), wrap azimuth to [0, 360) */
    if (zenith_deg < 0.0f)    zenith_deg = -zenith_deg;
    if (zenith_deg > 89.99f)  zenith_deg = 89.99f;
    if (az_deg < 0.0f)        az_deg += 360.0f;
    if (az_deg >= 360.0f)     az_deg -= 360.0f;

    int za = (int)(zenith_deg / 90.0f * (float)SKYMAP_ZEN_CELLS);
    int az = (int)(az_deg     / 360.0f * (float)SKYMAP_AZ_CELLS);
    if (za < 0) za = 0; if (za >= SKYMAP_ZEN_CELLS) za = SKYMAP_ZEN_CELLS - 1;
    if (az < 0) az = 0; if (az >= SKYMAP_AZ_CELLS) az = SKYMAP_AZ_CELLS - 1;

    s_map.cells[za * SKYMAP_AZ_CELLS + az]++;
    s_map.total++;
}

void skymap_get(skymap_t *out)
{
    *out = s_map;
}

uint32_t skymap_total(void)
{
    return s_map.total;
}