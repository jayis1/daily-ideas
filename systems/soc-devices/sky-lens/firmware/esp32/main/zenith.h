/* zenith.h — Δt → zenith angle + cos²θ fit */
#ifndef ZENITH_H
#define ZENITH_H
#include "sky_lens.h"

void  zenith_init(void);
void  zenith_add(float zenith_deg);
void  zenith_clear(void);
void  zenith_get_bins(uint32_t *bins, int n);
zenith_fit_t zenith_fit(void);   /* fit cos²θ, return I(0), chi2 */

#endif