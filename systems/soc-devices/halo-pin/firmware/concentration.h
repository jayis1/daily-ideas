/*
 * concentration.h — number concentration (#/L) + mass concentration (µg/m³)
 *
 * Converts raw per-bin particle counts into:
 *   - Number concentration (#/L) per channel
 *   - PM1, PM2.5, PM10 mass concentration (µg/m³)
 *
 * Mass is computed assuming spherical particles with density ρ = 1.65 g/cm³
 * (typical for atmospheric aerosol; configurable), using the bin midpoint
 * diameter and the count per bin. Humidity correction via κ-Köhler theory
 * (hygroscopic growth factor from RH) is optionally applied.
 */

#ifndef CONCENTRATION_H
#define CONCENTRATION_H

#include <stdint.h>

#define NUM_CHANNELS 16

void   concentration_init(void);
void   concentration_compute(const uint32_t counts[NUM_CHANNELS],
                              float volume_l,
                              float temp_c, float rh_pct,
                              float *pm1, float *pm25, float *pm10);

/* Configuration */
void   concentration_set_density(float rho_gcm3);
float  concentration_get_density(void);
void   concentration_set_hygroscopic(bool enable);
bool   concentration_get_hygroscopic(void);

/* Number concentration per channel (#/L) — filled by concentration_compute */
const float *concentration_number_per_l(void);

#endif /* CONCENTRATION_H */