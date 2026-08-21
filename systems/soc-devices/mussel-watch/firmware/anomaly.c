/*
 * Mussel Watch — Bivalve Biomonitoring Sensor
 * nRF52840 Firmware
 *
 * anomaly.c — Closure-event detection, rhythm analysis, stress scoring
 *
 * The anomaly detector runs three independent analyses on the gape-angle
 * time series and one on the water-quality context:
 *
 *  1. Closure-event detection
 *     A "closure event" is defined as the gape angle dropping below
 *     gape_threshold_deg for at least CLOSURE_EVENT_MIN_DURATION_S seconds.
 *     Each event is counted per-mussel. If closure persists beyond
 *     SUSTAINED_CLOSURE_ALERT_S, a sustained-closure alert fires.
 *
 *  2. Multi-mussel event detection
 *     If ≥2 mussels trigger a closure event within a 60-second window,
 *     this strongly suggests an environmental stressor (not individual
 *     behaviour). A MULTI_MUSSEL_EVENT alert fires.
 *
 *  3. Rhythm deviation
 *     The device maintains a 24-bin (hourly) profile of average gape angle.
 *     Over time, this reveals the mussel's circadian feeding rhythm
 *     (typically open during feeding hours, closed at night or during
 *     disturbance). If the current hour's average gape deviates by more
 *     than 50% from the historical mean for that bin, a RHYTHM_DEVIATION
 *     alert fires.
 *
 *  4. Water-quality anomaly
 *     A sudden temperature change (>TEMP_ANOMALY_DELTA_C between consecutive
 *     samples) or low dissolved oxygen (<DO_ANOMALY_LOW_MGL) triggers
 *     TEMP_ANOMALY or DO_ANOMALY alerts respectively.
 *
 * Copyright (c) 2026 SoC Device Inventions. MIT License.
 */

#include "anomaly.h"
#include "config.h"
#include <string.h>
#include <math.h>

/* Multi-mussel event window: if ≥2 mussels close within this window, flag */
#define MULTI_MUSSEL_WINDOW_MS  60000

/* Rhythm deviation threshold (fraction of historical mean) */
#define RHYTHM_DEVIATION_FRAC   0.50f

/* Minimum rhythm samples needed before deviation detection activates */
#define RHYTHM_MIN_SAMPLES      3

void anomaly_init(mussel_watch_state_t *st)
{
    memset(st->closure_start_ms, 0, sizeof(st->closure_start_ms));
    memset(st->closure_active, 0, sizeof(st->closure_active));
    memset(st->closure_events_hour, 0, sizeof(st->closure_events_hour));
    memset(st->rhythm_profile, 0, sizeof(st->rhythm_profile));
    st->rhythm_count = 0;
    st->last_hour_reset_ms = 0;
    st->current_alert = ALERT_NONE;
    st->alert_time_ms = 0;
    st->prev_temp_c = -999.0f;
}

const char *anomaly_alert_name(alert_code_t code)
{
    switch (code) {
        case ALERT_NONE:               return "Normal";
        case ALERT_CLOSURE_EVENT:      return "Closure event";
        case ALERT_SUSTAINED_CLOSURE:   return "Sustained closure (>10min)";
        case ALERT_RHYTHM_DEVIATION:   return "Rhythm deviation";
        case ALERT_MULTI_MUSSEL_EVENT: return "Multi-mussel closure (environmental)";
        case ALERT_TEMP_ANOMALY:       return "Temperature anomaly";
        case ALERT_DO_ANOMALY:         return "Low dissolved oxygen";
        case ALERT_LOW_BATTERY:        return "Low battery";
        default: return "Unknown";
    }
}

void anomaly_reset_hourly(mussel_watch_state_t *st)
{
    memset(st->closure_events_hour, 0, sizeof(st->closure_events_hour));
}

alert_code_t anomaly_update(mussel_watch_state_t *st, uint32_t now_ms)
{
    alert_code_t new_alert = ALERT_NONE;

    /* Check for hour rollover → reset hourly counters */
    if (now_ms - st->last_hour_reset_ms >= 3600000) {
        anomaly_reset_hourly(st);
        st->last_hour_reset_ms = now_ms;
    }

    /* Track simultaneous closures for multi-mussel detection */
    int closed_now = 0;
    uint32_t earliest_closure = 0xFFFFFFFF;

    for (int i = 0; i < st->n_mussels; i++) {
        float gape = st->gape_angle[i];
        if (gape < 0) continue;  /* sensor not valid */

        int is_closed = (gape < st->gape_threshold_deg);

        if (is_closed && !st->closure_active[i]) {
            /* Transition: open → closed. Start timer. */
            st->closure_start_ms[i] = now_ms;
            st->closure_active[i] = 1;
        } else if (!is_closed && st->closure_active[i]) {
            /* Transition: closed → open. Check if this was a closure event. */
            uint32_t dur = now_ms - st->closure_start_ms[i];
            if (dur >= (uint32_t)CLOSURE_EVENT_MIN_DURATION_S * 1000) {
                st->closure_events_hour[i]++;
                new_alert = ALERT_CLOSURE_EVENT;
            }
            st->closure_active[i] = 0;
            st->closure_start_ms[i] = 0;
        } else if (is_closed && st->closure_active[i]) {
            /* Still closed — check for sustained closure */
            uint32_t dur = now_ms - st->closure_start_ms[i];
            if (dur >= (uint32_t)st->closure_duration_s * 1000) {
                new_alert = ALERT_SUSTAINED_CLOSURE;
            }
            closed_now++;
            if (st->closure_start_ms[i] < earliest_closure)
                earliest_closure = st->closure_start_ms[i];
        }

        /* Per-hour closure-event threshold → stress indicator */
        if (st->closure_events_hour[i] >= CLOSURE_EVENTS_PER_HOUR_ALERT) {
            new_alert = ALERT_CLOSURE_EVENT;
        }
    }

    /* Multi-mussel event: ≥2 mussels closed simultaneously within window */
    if (closed_now >= 2 && earliest_closure != 0xFFFFFFFF) {
        if ((now_ms - earliest_closure) < MULTI_MUSSEL_WINDOW_MS) {
            new_alert = ALERT_MULTI_MUSSEL_EVENT;
        }
    }

    /* Update active alert if one was triggered */
    if (new_alert != ALERT_NONE) {
        st->current_alert = new_alert;
        st->alert_time_ms = now_ms;
    }

    return new_alert;
}

alert_code_t anomaly_check_water_quality(mussel_watch_state_t *st)
{
    /* Temperature anomaly: sudden change between consecutive samples */
    if (st->prev_temp_c > -100.0f) {
        float delta = fabsf(st->water_temp_c - st->prev_temp_c);
        if (delta >= TEMP_ANOMALY_DELTA_C) {
            st->current_alert = ALERT_TEMP_ANOMALY;
            return ALERT_TEMP_ANOMALY;
        }
    }
    st->prev_temp_c = st->water_temp_c;

    /* Dissolved oxygen anomaly: hypoxia */
    if (st->dissolved_o2_mgl > 0 && st->dissolved_o2_mgl < DO_ANOMALY_LOW_MGL) {
        st->current_alert = ALERT_DO_ANOMALY;
        return ALERT_DO_ANOMALY;
    }

    return ALERT_NONE;
}

void anomaly_update_rhythm(mussel_watch_state_t *st, uint32_t now_ms)
{
    /* Compute current hour bin (0–23) from boot-relative time.
     * In production, this would use RTC time. Here we use a simple
     * modulo-24-hours from boot. */
    uint32_t hours_since_boot = (now_ms / 3600000) % 24;
    int bin = (int)hours_since_boot;

    /* Average current gape across all valid mussels */
    float sum = 0;
    int count = 0;
    for (int i = 0; i < st->n_mussels; i++) {
        if (st->gape_angle[i] >= 0) {
            sum += st->gape_angle[i];
            count++;
        }
    }
    if (count == 0) return;

    float avg = sum / count;

    /* Check for rhythm deviation BEFORE updating the profile */
    if (st->rhythm_count >= RHYTHM_MIN_SAMPLES && st->rhythm_profile[bin][0] > 0) {
        float hist = st->rhythm_profile[bin][0];
        float dev = fabsf(avg - hist) / hist;
        if (dev > RHYTHM_DEVIATION_FRAC) {
            st->current_alert = ALERT_RHYTHM_DEVIATION;
        }
    }

    /* Update the running average for this bin (simple exponential smoothing) */
    if (st->rhythm_profile[bin][0] == 0) {
        st->rhythm_profile[bin][0] = avg;
    } else {
        st->rhythm_profile[bin][0] = 0.7f * st->rhythm_profile[bin][0] + 0.3f * avg;
    }
    st->rhythm_count++;
}