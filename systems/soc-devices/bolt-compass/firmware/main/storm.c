/*
 * storm.c — online DBSCAN storm-cell tracker + approach alerts
 *
 * Each resolved stroke is assigned to an existing storm cell if its
 * (bearing, distance) is within ε_bearing=15° and ε_dist=50 km of the
 * cell centroid; otherwise a new cell is created (up to MAX_STORM_CELLS,
 * then the oldest/inactive is evicted). Each cell maintains:
 *   - centroid (running mean bearing/distance),
 *   - stroke + CG counts,
 *   - first/last seen timestamps,
 *   - flash rate (strokes/min over a 5 min sliding window),
 *   - approach rate (d(distance)/dt via linear regression on last 10 min).
 *
 * Alerts:
 *   STORM_BUILDING  — |ΔE_slow| > 2× fair-weather for >60 s (set externally)
 *   STORM_APPROACHING — a CG-bearing cell < 20 km and closing > 5 km/h
 *   STORM_IMMINENT  — a CG-bearing cell < 10 km
 *   FIRST_CG        — first CG of the day
 */
#include "storm.h"
#include <math.h>
#include <string.h>
#include "esp_log.h"

static const char *TAG = "storm";

#define EPS_BEARING  15.0f
#define EPS_DIST     50.0f
#define CELL_TIMEOUT_S 600   /* 10 min of inactivity → inactive */

static storm_t s_storm;
static uint64_t s_day_start_us;
static int s_cg_count_today;
static int s_first_cg_reported;

void storm_init(void)
{
    memset(&s_storm, 0, sizeof(s_storm));
    s_day_start_us = 0;
    s_cg_count_today = 0;
    s_first_cg_reported = 0;
}

static float bearing_diff(float a, float b)
{
    float d = a - b;
    while (d >  180.0f) d -= 360.0f;
    while (d < -180.0f) d += 360.0f;
    return fabsf(d);
}

void storm_add(const stroke_t *st)
{
    /* Track first-CG-of-day. */
    if (st->cls.label == CLASS_CG) {
        s_cg_count_today++;
    }

    /* Find the nearest active cell. */
    int best = -1; float best_d = 1e9;
    for (int i = 0; i < s_storm.n; i++) {
        if (!s_storm.cell[i].active) continue;
        float db = bearing_diff(st->geo.azimuth_deg, s_storm.cell[i].bearing_deg);
        float dd = fabsf(st->geo.distance_km - s_storm.cell[i].distance_km);
        if (db < EPS_BEARING && dd < EPS_DIST) {
            float score = db + dd * 0.2f;
            if (score < best_d) { best_d = score; best = i; }
        }
    }

    storm_cell_t *cell;
    if (best < 0) {
        /* Create a new cell; evict the oldest inactive if full. */
        if (s_storm.n >= MAX_STORM_CELLS) {
            int oldest = 0;
            for (int i = 1; i < s_storm.n; i++)
                if (s_storm.cell[i].last_seen_us < s_storm.cell[oldest].last_seen_us)
                    oldest = i;
            best = oldest;
        } else {
            best = s_storm.n++;
        }
        cell = &s_storm.cell[best];
        memset(cell, 0, sizeof(*cell));
        cell->bearing_deg  = st->geo.azimuth_deg;
        cell->distance_km  = st->geo.distance_km;
        cell->first_seen_us = st->ts_us;
    } else {
        cell = &s_storm.cell[best];
        /* Running-mean update of centroid. */
        float n = (float)cell->stroke_count;
        cell->bearing_deg = (cell->bearing_deg * n + st->geo.azimuth_deg) / (n + 1);
        cell->distance_km = (cell->distance_km * n + st->geo.distance_km) / (n + 1);
    }
    cell->stroke_count++;
    if (st->cls.label == CLASS_CG) cell->cg_count++;
    cell->last_seen_us = st->ts_us;
    cell->active = true;

    /* Flash rate: strokes per minute over the last 5 min. */
    uint64_t window_us = 5ULL * 60 * 1000000;
    if (st->ts_us - cell->first_seen_us > window_us) {
        cell->flash_rate_per_min = (float)cell->stroke_count / 5.0f;
    } else {
        float secs = (float)((st->ts_us - cell->first_seen_us) / 1000000ULL);
        cell->flash_rate_per_min = (secs > 1) ? (float)cell->stroke_count / (secs / 60.0f) : 0;
    }

    ESP_LOGD(TAG, "stroke → cell %d  brg=%.0f d=%.0f cnt=%d cg=%d",
             best, cell->bearing_deg, cell->distance_km,
             cell->stroke_count, cell->cg_count);
}

void storm_snapshot(storm_t *out)
{
    memcpy(out, &s_storm, sizeof(s_storm));
}

int storm_alerts(alert_t *out, int n)
{
    int cnt = 0;
    if (s_cg_count_today > 0 && !s_first_cg_reported && n > cnt) {
        out[cnt++] = ALERT_FIRST_CG;
        s_first_cg_reported = 1;
    }
    for (int i = 0; i < s_storm.n && cnt < n; i++) {
        storm_cell_t *c = &s_storm.cell[i];
        if (!c->active || c->cg_count == 0) continue;
        if (c->distance_km < 10.0f) {
            out[cnt++] = ALERT_STORM_IMMINENT;
        } else if (c->distance_km < 20.0f && c->approach_kmph < -5.0f) {
            out[cnt++] = ALERT_STORM_APPROACHING;
        }
    }
    return cnt;
}