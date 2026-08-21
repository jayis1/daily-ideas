/*
 * storm.h — DBSCAN storm-cell tracker + approach alerts
 */
#ifndef BOLT_COMPASS_STORM_H
#define BOLT_COMPASS_STORM_H

#include "types.h"

void storm_init(void);

/* Add a resolved stroke to the tracker. */
void storm_add(const stroke_t *st);

/* Snapshot the current storm cells. */
void storm_snapshot(storm_t *out);

/* Pop pending alerts (returns count, fills out[]). */
int  storm_alerts(alert_t *out, int n);

#endif /* BOLT_COMPASS_STORM_H */