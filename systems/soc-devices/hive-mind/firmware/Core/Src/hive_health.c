/*
 * Hive Mind — Hive Health Score Computation
 * Fuses all sensor data into a single 0-100 health score
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "hive_health.h"
#include <math.h>

/* Health score components and weights:
 *
 * Weight trend (20%): Stable or increasing weight is good.
 *   Sudden drops indicate swarming or robbing.
 *
 * Temperature gradient (20%): Brood temperature should be 34-36°C.
 *   Floor-to-crown gradient indicates cluster health.
 *
 * Acoustic state (25%): QUEENRIGHT = good, QUEENLESS/DEAD = bad.
 *
 * Bee traffic balance (15%): Incoming ≈ Outgoing is healthy.
 *   Out >> In = robbing or orientation flights.
 *
 * Ambient conditions (10%): Moderate T/H is good for foraging.
 *   Extreme cold/hot reduces score.
 *
 * Battery (10%): Must be sufficient to operate.
 */

static float score_weight_trend(const sensor_data_t *data)
{
    /* Ideal: weight > 0 and stable
     * This is a simplified version; a real implementation would track
     * weight history over time. */
    float weight_kg = data->weight_g / 1000.0f;
    if (weight_kg < 0.5f) return 10.0f;    /* Very light hive = weak colony */
    if (weight_kg < 5.0f) return 40.0f;
    if (weight_kg < 15.0f) return 70.0f;
    if (weight_kg < 30.0f) return 85.0f;
    if (weight_kg < 50.0f) return 100.0f;   /* Heavy hive = strong colony */
    return 90.0f;                            /* Overweight = possible issues */
}

static float score_temperature(const sensor_data_t *data)
{
    float score = 50.0f;

    /* Brood temperature should be 34-36°C at mid-hive */
    float mid = data->temp_mid;
    if (mid >= 34.0f && mid <= 36.0f) {
        score += 30.0f;  /* Perfect brood temp */
    } else if (mid >= 32.0f && mid <= 38.0f) {
        score += 15.0f;  /* Acceptable */
    } else if (mid < 10.0f || mid > 45.0f) {
        score -= 30.0f;  /* Dangerous */
    }

    /* Temperature gradient: crown should be slightly warmer than floor
     * when cluster is active (winter) */
    float gradient = data->temp_crown - data->temp_floor;
    if (gradient >= 0.5f && gradient <= 5.0f) {
        score += 10.0f;  /* Natural gradient */
    }

    /* Crown temperature should not be extreme */
    if (data->temp_crown >= 20.0f && data->temp_crown <= 40.0f) {
        score += 10.0f;
    }

    if (score < 0) score = 0;
    if (score > 100) score = 100;
    return score;
}

static float score_acoustic(const sensor_data_t *data)
{
    switch (data->acoustic_class) {
        case AC_QUEENRIGHT: return 100.0f;
        case AC_FANNING:    return 75.0f;   /* Ventilating = warm but active */
        case AC_CLUSTERING: return 60.0f;   /* Cold-weather cluster = surviving */
        case AC_PIPING:     return 50.0f;   /* Queen activity = transitional */
        case AC_QUEENLESS:  return 20.0f;   /* Serious problem */
        case AC_ROBBING:    return 15.0f;   /* Under attack */
        case AC_SWARMING:   return 40.0f;   /* Natural but concerning */
        case AC_DEAD:       return 0.0f;    /* Colony lost */
        default:            return 50.0f;
    }
}

static float score_bee_traffic(const sensor_data_t *data)
{
    uint16_t in_count = data->bee_in;
    uint16_t out_count = data->bee_out;
    uint16_t total = in_count + out_count;

    if (total == 0) return 20.0f;  /* No activity = bad (unless winter) */

    /* Balance ratio: incoming should be close to outgoing */
    float ratio;
    if (out_count > 0) {
        ratio = (float)in_count / (float)out_count;
    } else {
        ratio = 2.0f;  /* All incoming, no outgoing */
    }

    float score = 50.0f;

    /* Ratio near 1.0 = balanced foraging */
    if (ratio >= 0.8f && ratio <= 1.2f) {
        score += 30.0f;
    } else if (ratio >= 0.5f && ratio <= 2.0f) {
        score += 15.0f;
    } else {
        score -= 10.0f;  /* Imbalanced = possible robbing */
    }

    /* High total activity = strong colony */
    if (total > 100) score += 20.0f;
    else if (total > 50) score += 10.0f;
    else if (total > 20) score += 5.0f;

    if (score > 100) score = 100;
    if (score < 0) score = 0;
    return score;
}

static float score_ambient(const sensor_data_t *data)
{
    float score = 70.0f;  /* Baseline: neutral conditions */

    /* Moderate temperature = good for foraging */
    if (data->ambient_t >= 15.0f && data->ambient_t <= 30.0f) {
        score += 20.0f;
    } else if (data->ambient_t >= 5.0f && data->ambient_t <= 35.0f) {
        score += 10.0f;
    } else {
        score -= 20.0f;  /* Extreme weather */
    }

    /* Moderate humidity = good */
    if (data->ambient_h >= 40.0f && data->ambient_h <= 70.0f) {
        score += 10.0f;
    }

    if (score > 100) score = 100;
    if (score < 0) score = 0;
    return score;
}

static float score_battery(const sensor_data_t *data)
{
    float vbat = data->vbat;

    /* LiFePO4 voltage: 3.2V nominal, 3.65V full, 2.5V empty */
    if (vbat >= 3.4f) return 100.0f;
    if (vbat >= 3.2f) return 80.0f;
    if (vbat >= 3.0f) return 50.0f;
    if (vbat >= 2.8f) return 20.0f;
    return 5.0f;  /* Critically low */
}

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

float hive_health_compute(const sensor_data_t *data)
{
    float s_weight   = score_weight_trend(data);
    float s_temp     = score_temperature(data);
    float s_acoustic = score_acoustic(data);
    float s_traffic  = score_bee_traffic(data);
    float s_ambient  = score_ambient(data);
    float s_battery  = score_battery(data);

    /* Weighted sum */
    float health = s_weight   * 0.20f +
                   s_temp     * 0.20f +
                   s_acoustic * 0.25f +
                   s_traffic  * 0.15f +
                   s_ambient  * 0.10f +
                   s_battery  * 0.10f;

    if (health < 0) health = 0;
    if (health > 100) health = 100;

    return health;
}

const char *hive_health_label(float score)
{
    if (score >= 80) return "EXCELLENT";
    if (score >= 60) return "GOOD";
    if (score >= 40) return "FAIR";
    if (score >= 20) return "POOR";
    return "CRITICAL";
}