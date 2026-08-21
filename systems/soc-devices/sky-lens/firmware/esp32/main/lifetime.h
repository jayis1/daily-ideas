/* lifetime.h — muon-lifetime (prompt–delayed) mode + exponential fit */
#ifndef LIFETIME_H
#define LIFETIME_H
#include "sky_lens.h"

void lifetime_init(void);
void lifetime_add_delay(float dt_us);
void lifetime_clear(void);
void lifetime_get_delays(uint32_t *out, int n);
lifetime_result_t lifetime_fit(void);    /* returns τ_µ + error + bg */

#endif