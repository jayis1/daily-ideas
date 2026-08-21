/**
 * fermentation.h — Fermentation Stage Classification Engine
 * 
 * Combines gravity, CO₂, temperature, and pH readings to classify
 * the current fermentation stage and compute an activity index.
 */

#ifndef FERMENTATION_H
#define FERMENTATION_H

#include <stdint.h>
#include <stdbool.h>

/* Fermentation stages */
typedef enum {
    FERMENT_LAG      = 0,  /* Yeast adapting, gravity high, CO₂ flat */
    FERMENT_ACTIVE   = 1,  /* Krausen forming, gravity dropping, CO₂ rising */
    FERMENT_PEAK     = 2,  /* Maximum activity, gravity plateau, CO₂ peak */
    FERMENT_SLOWING  = 3,  /* Activity declining, gravity slowly dropping */
    FERMENT_FINISHED = 4,  /* Gravity stable, CO₂ near zero */
    FERMENT_STUCK    = 5,  /* No change for >48h, possible stuck ferment */
} ferment_stage_t;

/* Fermentation state — maintained across readings */
typedef struct {
    ferment_stage_t stage;          /* Current classified stage */
    float activity_index;           /* 0-100 activity metric */
    float gravity_history[48];      /* Last 48 gravity readings (48 hours @ 1/hr) */
    float co2_history[48];           /* Last 48 CO₂ readings */
    float temp_history[48];          /* Last 48 temperature readings */
    uint32_t history_count;         /* Number of valid history entries */
    uint32_t stable_count;          /* Consecutive readings with <0.001 SG change */
    uint32_t hours_elapsed;         /* Estimated hours since start */
    float gravity_start;            /* Initial gravity (OG) */
    float gravity_current;          /* Most recent gravity */
    float gravity_rate;             /* SG change per hour */
    float co2_rate;                 /* CO₂ change per hour */
    int8_t trend;                   /* -2 to +2: trending direction */
} fermentation_state_t;

/* Configuration */
typedef struct {
    float og;                      /* Original gravity (e.g., 1.050) */
    float fg_target;               /* Expected final gravity (e.g., 1.010) */
    uint32_t stuck_threshold_hr;   /* Hours without change = stuck (default: 48) */
    float stable_sg_delta;          /* SG change threshold for "stable" (default: 0.001) */
    uint32_t sample_interval_min;  /* Minutes between samples (default: 1) */
} fermentation_config_t;

/**
 * Initialize the fermentation engine.
 * @param config Configuration parameters (NULL for defaults)
 */
void fermentation_init(const fermentation_config_t *config);

/**
 * Update fermentation state with new sensor readings.
 * Call this on every sample interval.
 * @param temperature Current temperature in °C
 * @param gravity Current specific gravity
 * @param co2_ppm Current CO₂ reading in ppm
 * @param ph Current pH reading
 * @param pressure Current pressure in hPa
 */
void fermentation_update(float temperature, float gravity, 
                          uint16_t co2_ppm, float ph, float pressure);

/**
 * Get the current fermentation stage classification.
 * @return Current ferment_stage_t
 */
ferment_stage_t fermentation_get_stage(void);

/**
 * Get the current activity index (0-100).
 * 0 = no activity, 100 = peak krausen.
 * @return Activity index
 */
float fermentation_get_activity_index(void);

/**
 * Get the full fermentation state.
 * @param state Pointer to state structure to fill
 */
void fermentation_get_state(fermentation_state_t *state);

/**
 * Get the gravity trend direction.
 * @return -2 (dropping fast), -1 (dropping), 0 (stable), +1 (rising), +2 (rising fast)
 */
int8_t fermentation_get_trend(void);

/**
 * Estimate time remaining until fermentation is complete.
 * Based on current gravity rate and target FG.
 * @return Estimated hours remaining, or -1 if unknown
 */
float fermentation_estimate_time_remaining(void);

/**
 * Get a human-readable string for a fermentation stage.
 * @param stage The stage enum value
 * @return String like "LAG", "ACTIVE", "PEAK", etc.
 */
const char *fermentation_stage_str(ferment_stage_t stage);

/**
 * Check if any alerts should be raised.
 * @return Alert flags bitmask (see below)
 */
#define ALERT_STUCK_FERMENT  0x01
#define ALERT_HIGH_TEMP      0x02  /* > 30°C */
#define ALERT_LOW_TEMP       0x04  /* < 10°C */
#define ALERT_FINISHED       0x08
#define ALERT_PH_LOW         0x10  /* pH < 2.5 */
#define ALERT_PH_HIGH        0x20  /* pH > 4.4 */
uint8_t fermentation_get_alerts(void);

/**
 * Reset the fermentation engine for a new batch.
 * @param og Original gravity of the new batch
 */
void fermentation_reset(float og);

#endif /* FERMENTATION_H */