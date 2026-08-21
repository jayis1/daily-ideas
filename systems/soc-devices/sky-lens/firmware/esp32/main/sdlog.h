/* sdlog.h — FatFS event CSV + daily JSON rollup */
#ifndef SDLOG_H
#define SDLOG_H
#include "sky_lens.h"

void sdlog_init(void);
void sdlog_write_event(const event_t *ev);
void sdlog_write_daily(const skymap_t *m, const zenith_fit_t *z,
                       const daily_t *d, const lifetime_result_t *lf);

#endif