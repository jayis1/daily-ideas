/*
 * sdlog.h — FatFS CSV + binary waveform logging
 */
#ifndef BOLT_COMPASS_SDLOG_H
#define BOLT_COMPASS_SDLOG_H

#include "types.h"

int  sdlog_mount(void);

/* Append a sferic row to today's CSV + write the waveform blob. */
void sdlog_sferic(const stroke_t *st);

/* Flush pending file writes. */
void sdlog_flush(void);

#endif /* BOLT_COMPASS_SDLOG_H */