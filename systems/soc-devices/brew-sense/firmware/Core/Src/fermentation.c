/**
 * fermentation.c — Fermentation Stage Classification Engine
 * 
 * Processes sensor data to classify fermentation stage, compute
 * activity index, and detect anomalies (stuck fermentation, etc.)
 */

#include "fermentation.h"
#include <string.h>
#include <math.h>

#define HISTORY_SIZE      48
#define STUCK_THRESHOLD   48    /* Hours without change = stuck */
#define STABLE_DELTA      0.001f  /* SG change threshold for "stable" */
#define TREK_WINDOW       6     /* Number of samples for trend calculation */

static fermentation_state_t s_state;
static fermentation_config_t s_config;

/*----------------------------------------------------------------------------*/

void fermentation_init(const fermentation_config_t *config) {
    if (config) {
        s_config = *config;
    } else {
        s_config.og = 1.050f;
        s_config.fg_target = 1.010f;
        s_config.stuck_threshold_hr = STUCK_THRESHOLD;
        s_config.stable_sg_delta = STABLE_DELTA;
        s_config.sample_interval_min = 1;
    }
    
    memset(&s_state, 0, sizeof(s_state));
    s_state.gravity_start = s_config.og;
    s_state.stage = FERMENT_LAG;
}

/*----------------------------------------------------------------------------*/

void fermentation_update(float temperature, float gravity,
                          uint16_t co2_ppm, float ph, float pressure) {
    /* Shift history and add new readings */
    if (s_state.history_count >= HISTORY_SIZE) {
        /* Shift history left by 1 */
        memmove(&s_state.gravity_history[0], &s_state.gravity_history[1],
                (HISTORY_SIZE - 1) * sizeof(float));
        memmove(&s_state.co2_history[0], &s_state.co2_history[1],
                (HISTORY_SIZE - 1) * sizeof(float));
        memmove(&s_state.temp_history[0], &s_state.temp_history[1],
                (HISTORY_SIZE - 1) * sizeof(float));
        s_state.history_count = HISTORY_SIZE - 1;
    }
    
    s_state.gravity_history[s_state.history_count] = gravity;
    s_state.co2_history[s_state.history_count] = (float)co2_ppm;
    s_state.temp_history[s_state.history_count] = temperature;
    s_state.history_count++;
    
    s_state.gravity_current = gravity;
    s_state.hours_elapsed = s_state.history_count * s_config.sample_interval_min / 60;
    
    /* Calculate gravity rate of change (SG per hour) */
    if (s_state.history_count >= 2) {
        float prev = s_state.gravity_history[s_state.history_count - 2];
        float curr = s_state.gravity_history[s_state.history_count - 1];
        float dt_hours = (float)s_config.sample_interval_min / 60.0f;
        s_state.gravity_rate = (prev - curr) / dt_hours;  /* Positive = dropping */
    }
    
    /* Calculate CO₂ rate of change (ppm per hour) */
    if (s_state.history_count >= 2) {
        float prev_co2 = s_state.co2_history[s_state.history_count - 2];
        float curr_co2 = s_state.co2_history[s_state.history_count - 1];
        float dt_hours = (float)s_config.sample_interval_min / 60.0f;
        s_state.co2_rate = (curr_co2 - prev_co2) / dt_hours;  /* Positive = rising */
    }
    
    /* Check for stable gravity (no change) */
    if (s_state.history_count >= 2) {
        float delta = fabsf(s_state.gravity_history[s_state.history_count - 1] -
                            s_state.gravity_history[s_state.history_count - 2]);
        if (delta < s_config.stable_sg_delta) {
            s_state.stable_count++;
        } else {
            s_state.stable_count = 0;
        }
    }
    
    /* Calculate trend (-2 to +2) */
    if (s_state.history_count >= TREK_WINDOW) {
        float recent = 0, older = 0;
        int n = TREK_WINDOW / 2;
        for (int i = 0; i < n; i++) {
            recent += s_state.gravity_history[s_state.history_count - 1 - i];
            older += s_state.gravity_history[s_state.history_count - n - 1 - i];
        }
        recent /= n;
        older /= n;
        float delta_sg = older - recent;  /* Positive = gravity dropping */
        
        if (delta_sg > 0.005f) s_state.trend = -2;   /* Dropping fast (active) */
        else if (delta_sg > 0.002f) s_state.trend = -1;  /* Dropping slowly */
        else if (delta_sg > -0.002f) s_state.trend = 0;  /* Stable */
        else if (delta_sg > -0.005f) s_state.trend = 1;   /* Rising slowly */
        else s_state.trend = 2;  /* Rising fast (anomaly) */
    }
    
    /* Calculate activity index (0-100) */
    float activity = 0.0f;
    
    /* Component 1: Gravity change rate (0-40 points) */
    float gravity_rate_score = fminf(fabsf(s_state.gravity_rate) * 2000.0f, 40.0f);
    activity += gravity_rate_score;
    
    /* Component 2: CO₂ level (0-30 points) */
    float co2_score = fminf((float)co2_ppm / 33.0f, 30.0f);  /* 1000 ppm = 30 pts */
    activity += co2_score;
    
    /* Component 3: CO₂ rate (0-30 points) */
    float co2_rate_score = fminf(s_state.co2_rate / 3.3f, 30.0f);  /* 100 ppm/hr = 30 pts */
    activity += co2_rate_score;
    
    s_state.activity_index = fminf(fmaxf(activity, 0.0f), 100.0f);
    
    /* Classify fermentation stage */
    float sg = gravity;
    float hours_stable = s_state.stable_count * s_config.sample_interval_min / 60.0f;
    
    if (sg > 1.060f && s_state.activity_index < 15.0f && co2_ppm < 600) {
        s_state.stage = FERMENT_LAG;  /* High gravity, low activity = lag phase */
    } else if (s_state.gravity_rate > 0.001f && co2_ppm > 500) {
        s_state.stage = FERMENT_ACTIVE;  /* Gravity dropping, CO₂ rising */
    } else if (s_state.activity_index >= 90.0f && sg > 1.020f && sg < 1.040f) {
        s_state.stage = FERMENT_PEAK;  /* Peak activity, plateau gravity */
    } else if (s_state.gravity_rate > 0.0f && s_state.gravity_rate < 0.002f && co2_ppm > 200) {
        s_state.stage = FERMENT_SLOWING;  /* Still dropping, but slowly */
    } else if (sg < 1.015f && hours_stable > 24.0f && co2_ppm < 100) {
        s_state.stage = FERMENT_FINISHED;  /* Low gravity, stable, low CO₂ */
    } else if (hours_stable > (float)s_config.stuck_threshold_hr && s_state.activity_index < 5.0f) {
        s_state.stage = FERMENT_STUCK;  /* No change for too long */
    }
    /* Default: keep current stage */
}

/*----------------------------------------------------------------------------*/

ferment_stage_t fermentation_get_stage(void) {
    return s_state.stage;
}

/*----------------------------------------------------------------------------*/

float fermentation_get_activity_index(void) {
    return s_state.activity_index;
}

/*----------------------------------------------------------------------------*/

void fermentation_get_state(fermentation_state_t *state) {
    memcpy(state, &s_state, sizeof(fermentation_state_t));
}

/*----------------------------------------------------------------------------*/

int8_t fermentation_get_trend(void) {
    return s_state.trend;
}

/*----------------------------------------------------------------------------*/

float fermentation_estimate_time_remaining(void) {
    if (s_state.gravity_rate <= 0.0001f) {
        return -1.0f;  /* Can't estimate if not dropping */
    }
    
    float sg_remaining = s_state.gravity_current - s_config.fg_target;
    if (sg_remaining <= 0.0f) {
        return 0.0f;  /* Already at or below target */
    }
    
    float hours_remaining = sg_remaining / s_state.gravity_rate;
    return hours_remaining;
}

/*----------------------------------------------------------------------------*/

const char *fermentation_stage_str(ferment_stage_t stage) {
    switch (stage) {
        case FERMENT_LAG:      return "LAG";
        case FERMENT_ACTIVE:   return "ACTIVE";
        case FERMENT_PEAK:     return "PEAK";
        case FERMENT_SLOWING:  return "SLOWING";
        case FERMENT_FINISHED: return "FINISHED";
        case FERMENT_STUCK:    return "STUCK";
        default:               return "UNKNOWN";
    }
}

/*----------------------------------------------------------------------------*/

uint8_t fermentation_get_alerts(void) {
    uint8_t alerts = 0;
    
    if (s_state.stage == FERMENT_STUCK) {
        alerts |= ALERT_STUCK_FERMENT;
    }
    if (s_state.stage == FERMENT_FINISHED) {
        alerts |= ALERT_FINISHED;
    }
    
    /* Check temperature alerts using latest history */
    if (s_state.history_count > 0) {
        float temp = s_state.temp_history[s_state.history_count - 1];
        if (temp > s_config.stuck_threshold_hr) {  /* Reusing field as temp threshold (simplified) */
            /* Actually, we should use the alarm_config_t thresholds */
            /* For now, use hardcoded limits */
            if (temp > 30.0f) alerts |= ALERT_HIGH_TEMP;
            if (temp < 10.0f) alerts |= ALERT_LOW_TEMP;
        }
    }
    
    return alerts;
}

/*----------------------------------------------------------------------------*/

void fermentation_reset(float og) {
    memset(&s_state, 0, sizeof(s_state));
    s_state.gravity_start = og;
    s_state.gravity_current = og;
    s_state.stage = FERMENT_LAG;
    s_config.og = og;
}