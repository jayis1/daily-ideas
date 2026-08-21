/*
 * slow_wave.h — Slow-wave potential analysis
 * Phyto Pulse — Plant Electrophysiology Recorder
 *
 * Tracks gradual (minutes) voltage shifts associated with light/dark
 * transitions, water stress, and circadian rhythms.
 */

#ifndef SLOW_WAVE_H
#define SLOW_WAVE_H

#include <stdint.h>
#include <stdbool.h>

/* Slow-wave update interval (60 s) */
#define SWP_INTERVAL_MS  60000

/* SWP result */
typedef struct {
    uint32_t timestamp_ms;
    float    mean_mv;       /* 60 s windowed mean */
    float    peak_to_peak;  /* peak-to-peak in window */
    float    slope_mV_per_min;  /* trend slope */
} swp_result_t;

void slow_wave_init(void);

/* Feed a new sample (input-referred voltage in mV) */
void slow_wave_feed(float voltage_mv, uint32_t timestamp_ms);

/* Check if a new SWP result is available (every 60 s) */
bool slow_wave_result_available(void);

/* Get the latest SWP result */
bool slow_wave_get_result(swp_result_t *result);

/* Get current 60 s mean (for display) */
float slow_wave_get_current_mean(void);

#endif /* SLOW_WAVE_H */