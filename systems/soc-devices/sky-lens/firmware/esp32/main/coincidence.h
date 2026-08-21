/* coincidence.h — RMT-based SiPM discriminator timestamping + coincidence logic */
#ifndef COINCIDENCE_H
#define COINCIDENCE_H
#include "sky_lens.h"

void     coincidence_init(void);
void     coincidence_set_window_ns(int32_t ns);
int32_t  coincidence_get_window_ns(void);
bool     coincidence_pop(event_t *out);   /* returns true if an event was popped */
uint64_t coincidence_count(void);

/* Edge arrival hooks (called by the RMT ISR or the simulator).
 * Timestamps are in picoseconds since boot. */
void     coincidence_on_edge0(int64_t ts_ps);
void     coincidence_on_edge1(int64_t ts_ps);

#endif